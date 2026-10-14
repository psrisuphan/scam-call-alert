"""Progressive session engine. All audio positions are integer 16 kHz samples.

This is independent of HTTP and Android. Injected STT/model adapters enable
invariant tests without using real-model scores as experiment evidence.
"""
from __future__ import annotations
import array
import bisect
import hashlib
import json
import math
import os
from pathlib import Path
import threading
import time
import uuid


class ProtocolError(ValueError):
    pass


class Session:
    def __init__(self, config, recognizer, classifier, context_builder, *, mode,
                 approach, evidence_root, save=False, recording_id=None):
        if mode not in {"recorded", "microphone"}:
            raise ProtocolError("Invalid input mode")
        if approach not in {"latest", "recent", "accumulated"}:
            raise ProtocolError("Invalid context approach")
        self.id = uuid.uuid4().hex
        self.config, self.recognizer, self.classifier = config, recognizer, classifier
        self.context_builder, self.mode, self.approach = context_builder, mode, approach
        self.recording_id = recording_id
        self.save = bool(save or mode == "recorded")
        self.directory = Path(evidence_root) / self.id
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.audio = array.array("h")
        self.received_samples = 0
        self.audio_signal = None
        self.receipts = {}
        self.seq, self.processed_samples, self.window_end = 0, 0, 0
        self.frames, self.frame_times = [], []
        self.frame_groups, self.characters = [], []
        self.segments_dirty = False
        self.boundary_sequence = 0
        self.segments = {}
        self.version, self.transcript = 0, ""
        self.prediction, self.warning = None, False
        self.state, self.error = "active", None
        self.stt_busy = self.classifier_busy = False
        self.stt_windows_completed = 0
        self.stt_last_duration_seconds = None
        self.stt_active_window = None
        self.stt_active_started = None
        self.microphone_failure_diagnostics = None
        self.pending = None
        self.last_context = None
        self.history, self.events = [], []
        self.created = time.monotonic()
        self.last_contact = self.created
        self.schedule_origin = None if config.get('require_native_start_signal') else self.created
        self.finishing_started = None
        self.resources = []
        self._event("session_created", mode=mode, approach=approach,
                    recording_id=recording_id, configuration=config)
        self.stt_thread = threading.Thread(target=self._stt_loop, daemon=True)
        self.predict_thread = threading.Thread(target=self._prediction_loop, daemon=True)
        self.schedule_thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self.stt_thread.start()
        self.predict_thread.start()
        self.schedule_thread.start()
        if config.get("resource_sampling_interval_seconds"):
            threading.Thread(target=self._resource_loop, daemon=True).start()

    def _event(self, kind, **values):
        row = {"event_id": len(self.events), "session_id": self.id, "kind": kind,
               "host_elapsed_s": time.monotonic() - self.created,
               "host_wall_time_s": time.time(), **values}
        self.events.append(row)
        if self.save:
            self.directory.mkdir(parents=True, exist_ok=True)
            with (self.directory / "events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary = self.directory / 'snapshot.tmp'
            with temporary.open('w', encoding='utf-8') as stream:
                json.dump(self.snapshot(), stream, ensure_ascii=False, allow_nan=False)
                stream.flush(); os.fsync(stream.fileno())
            temporary.replace(self.directory / 'snapshot.json')

    def touch(self):
        with self.lock:
            self.last_contact = time.monotonic()

    def begin_timing(self, native_origin=None, origin_source='android_monotonic'):
        with self.condition:
            if self.schedule_origin is None:
                self.schedule_origin = time.monotonic()
                values = {'host_origin_monotonic_s': self.schedule_origin,
                          'origin_source': origin_source}
                if native_origin is not None:
                    values['client_origin_monotonic_ms'] = native_origin
                self._event('scheduler_origin', **values)
                self.condition.notify_all()

    def _resource_loop(self):
        import psutil
        process = psutil.Process()
        process.cpu_percent(None)
        while True:
            time.sleep(self.config['resource_sampling_interval_seconds'])
            with self.lock:
                if self.state in {'complete', 'cancelled', 'failed'}:
                    return
                values = {'process_cpu_percent': process.cpu_percent(None),
                          'process_rss_bytes': process.memory_info().rss,
                          'host_available_memory_bytes': psutil.virtual_memory().available}
                try:
                    import torch
                    if torch.backends.mps.is_available():
                        values['mps_driver_allocated_bytes'] = torch.mps.driver_allocated_memory()
                except Exception:
                    pass
                self._event('resource_sample', **values)

    def _check_lease(self):
        limit = self.config.get('session_lease_seconds')
        if limit and time.monotonic() - self.last_contact > limit:
            self.fail('E_CLIENT_DISCONNECTED', 'Client stopped contacting the session')

    def enable_save(self):
        with self.lock:
            if self.save:
                return
            self.directory.mkdir(parents=True, exist_ok=False)
            self.save = True
            with (self.directory / "events.jsonl").open("x", encoding="utf-8") as stream:
                for row in self.events:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            with (self.directory / "audio.pcm").open("xb") as stream:
                stream.write(self.audio.tobytes())
            self._event("evidence_save_enabled")

    def accept_audio(self, seq, start_sample, end_sample, pcm, available_ms,
                     available_monotonic_ms=None, availability_clock='client_monotonic'):
        with self.condition:
            if self.state != "active":
                raise ProtocolError("Session does not accept more audio")
            if self.schedule_origin is None:
                raise ProtocolError('Native playback/capture start has not been registered')
            receipt = (start_sample, end_sample, hashlib.sha256(pcm).hexdigest(), available_ms, available_monotonic_ms)
            if type(seq) is int and seq in self.receipts and self.receipts[seq] == receipt:
                self._event("duplicate_audio_receipt", sequence=seq, disposition="exact_idempotent_retry")
                return self.snapshot()
            if (type(seq) is not int or seq != self.seq or type(start_sample) is not int
                    or start_sample != len(self.audio) or end_sample <= start_sample
                    or len(pcm) != (end_sample - start_sample) * 2):
                self._event("audio_rejected", sequence=seq, start=start_sample, end=end_sample)
                self.fail("E_AUDIO_SEQUENCE", "Missing, duplicate or nonchronological audio")
                raise ProtocolError("Audio range/sequence does not match the accepted stream")
            if not math.isfinite(available_ms) or available_ms < end_sample / 16:
                self._event("audio_rejected_future", sequence=seq)
                raise ProtocolError("Audio exceeds declared availability position")
            if available_monotonic_ms is not None and (not math.isfinite(available_monotonic_ms) or available_monotonic_ms < 0):
                raise ProtocolError('Invalid availability observation timestamp')
            if availability_clock not in {'client_monotonic', 'host_monotonic'}:
                raise ProtocolError('Invalid availability clock source')
            queued = len(self.audio) - self.processed_samples
            if queued + end_sample - start_sample > self.config["max_queued_audio_seconds"] * 16000:
                self._event("queue_limit", queued_samples=queued)
                if self.mode == "microphone":
                    self.fail("E_OVERLOAD", "Analysis cannot keep up")
                raise ProtocolError("E_QUEUE_LIMIT")
            data = array.array("h")
            data.frombytes(pcm)
            peak = max((abs(value) for value in data), default=0) / 32768
            rms = math.sqrt(sum(value * value for value in data) / max(1, len(data))) / 32768
            self.audio_signal = {"peak": peak, "rms": rms,
                                 "rms_dbfs": 20 * math.log10(max(rms, 1e-6))}
            self.audio.extend(data)
            self.received_samples = len(self.audio)
            self.receipts[seq] = receipt
            self.seq += 1
            clock_values = {f'available_{availability_clock}_monotonic_ms': available_monotonic_ms}
            self._event("audio_accepted", sequence=seq, start_sample=start_sample,
                        end_sample=end_sample, available_elapsed_ms=available_ms,
                        **clock_values, pcm_sha256=hashlib.sha256(pcm).hexdigest())
            if self.save:
                with (self.directory / "audio.pcm").open("ab") as stream:
                    stream.write(pcm)
                    stream.flush()
            self.condition.notify_all()
            return self.snapshot()

    def finish(self):
        with self.condition:
            if self.state == "active":
                if not self.audio:
                    self.fail("E_EMPTY_AUDIO", "No audio was received")
                    return self.snapshot()
                self.state = "finishing"
                self.finishing_started = time.monotonic()
                self._event("natural_completion_requested", final_sample=len(self.audio))
                self.condition.notify_all()
            return self.snapshot()

    def cancel(self):
        with self.condition:
            terminal = self.state in {"complete", "failed"}
            if self.state not in {"complete", "failed"}:
                self.state = "cancelled"
            self.pending = None
            self._event("session_closed" if terminal else "cancelled", final_state=self.state)
            self._clear_unsaved()
            self.condition.notify_all()

    def fail(self, code, message):
        with self.condition:
            if self.mode == "microphone" and not self.save:
                now = time.monotonic()
                source = getattr(self, "microphone_source", None)
                signal = dict(self.audio_signal) if self.audio_signal else None
                active_stt_elapsed = (now - self.stt_active_started
                                      if self.stt_busy and self.stt_active_started is not None else None)
                self.microphone_failure_diagnostics = {
                    "accepted_samples": self.received_samples,
                    "processed_samples": self.processed_samples,
                    "queued_samples": max(0, len(self.audio) - self.processed_samples),
                    "last_signal_metrics": signal,
                    "stt_busy": self.stt_busy,
                    "classifier_busy": self.classifier_busy,
                    "stt_windows_completed": self.stt_windows_completed,
                    "last_completed_stt_seconds": self.stt_last_duration_seconds,
                    "active_stt_window": ({"start_sample": self.stt_active_window[0],
                                            "end_sample": self.stt_active_window[1],
                                            "elapsed_seconds": active_stt_elapsed}
                                           if self.stt_active_window else None),
                    "capture": source.snapshot() if source else None,
                }
            self.state, self.error = "failed", {"code": code, "message": message}
            self.pending = None
            self._event("failure", error=self.error)
            self._clear_unsaved()
            self.condition.notify_all()

    def _clear_unsaved(self):
        if self.mode == "microphone" and not self.save:
            self.audio = array.array("h")
            self.frames, self.frame_times, self.events = [], [], []
            self.frame_groups, self.characters = [], []
            self.segments, self.transcript, self.history = {}, "", []
            self.prediction, self.warning = None, False
            self.audio_signal = None

    def snapshot(self):
        with self.lock:
            return {"session_id": self.id, "mode": self.mode, "state": self.state,
                    "version": self.version, "transcript": self.transcript,
                    "segments": list(self.segments.values()), "prediction": self.prediction,
                    "warning": self.warning, "error": self.error,
                    "stt_busy": self.stt_busy, "classifier_busy": self.classifier_busy,
                    "audio_samples": self.received_samples, "processed_samples": self.processed_samples,
                    "audio_signal": self.audio_signal,
                    "queued_seconds": max(0, len(self.audio) - self.processed_samples) / 16000,
                    "save_evidence": self.save, "recording_id": self.recording_id,
                    "microphone_failure_diagnostics": self.microphone_failure_diagnostics,
                    "microphone_capture": self.microphone_source.snapshot() if getattr(self, 'microphone_source', None) else None}

    def _next_window(self):
        window = round(self.config["stt_window_seconds"] * 16000)
        overlap = round(self.config["stt_overlap_seconds"] * 16000)
        start = max(0, self.window_end - overlap)
        target = start + window
        if len(self.audio) >= target:
            return start, target
        if self.state == "finishing" and len(self.audio) > self.window_end:
            return start, len(self.audio)
        return None

    def _stt_loop(self):
        while True:
            with self.condition:
                self._check_lease()
                if self.state in {"failed", "cancelled", "complete"}:
                    return
                pair = self._next_window()
                if pair is None:
                    self._maybe_complete()
                    self.condition.wait(timeout=0.2)
                    continue
                start, end = pair
                pcm = self.audio[start:end].tobytes()
                self.stt_busy = True
                self.stt_active_window = (start, end)
                self.stt_active_started = time.monotonic()
                self._event("stt_started", start_sample=start, end_sample=end)
            try:
                result = self.recognizer.recognize(pcm)
                with self.condition:
                    self.stt_last_duration_seconds = time.monotonic() - self.stt_active_started
                    self.stt_windows_completed += 1
                    self.stt_active_window = None
                    self.stt_active_started = None
                    if self.state in {"failed", "cancelled"}:
                        self.stt_busy = False
                        return
                    self._reconcile(start, end, result)
                    self.window_end = self.processed_samples = end
                    self.stt_busy = False
                    self.condition.notify_all()
            except Exception as exc:
                with self.condition:
                    self.stt_last_duration_seconds = (time.monotonic() - self.stt_active_started
                                                       if self.stt_active_started is not None else None)
                    self.stt_active_window = None
                    self.stt_active_started = None
                self.stt_busy = False
                self.fail("E_STT_FAILED", f"STT processing failed ({type(exc).__name__})")
                return

    def _reconcile(self, start, end, result):
        # The cut is an acoustic frame ownership convention, not a claimed word
        # timestamp. No fuzzy matching/deletion of repeated speech is applied.
        cut = start / 16000 + (self.config["stt_overlap_seconds"] / 2 if start else 0)
        keep = sum(t < cut for t in self.frame_times)
        new = [(token, start / 16000 + t) for token, t in zip(result["frames"], result["times"])
               if start / 16000 + t >= cut]
        groups = []
        for _, timestamp in new:
            if timestamp < self.window_end / 16000 and self.frame_times:
                index = max(0, bisect.bisect_right(self.frame_times, timestamp) - 1)
                groups.append(self.frame_groups[index])
            else:
                groups.append(None)
        self.frame_groups = self.frame_groups[:keep] + groups
        self.frames = self.frames[:keep] + [x[0] for x in new]
        self.frame_times = self.frame_times[:keep] + [x[1] for x in new]
        text, chars = self.recognizer.decode(self.frames)
        self.characters = chars
        changed = text != self.transcript
        self.transcript = text
        if changed:
            self.version += 1
            self.segments_dirty = True
        self._event("stt_completed", start_sample=start, end_sample=end,
                    raw_text=result["text"], frames=result["frames"], frame_times=result["times"],
                    version=self.version, transcript=text, resources=result.get("resources"))
        self.condition.notify_all()

    def _schedule_loop(self):
        interval = self.config['update_interval_seconds']
        next_boundary = None
        while True:
            with self.condition:
                self._check_lease()
                if self.state in {'complete','cancelled','failed'}:
                    return
                if self.schedule_origin is None:
                    self.condition.wait(timeout=0.2)
                    continue
                if next_boundary is None:
                    next_boundary = self.schedule_origin + interval
                now = time.monotonic()
                final = (self.state == 'finishing' and self.processed_samples == len(self.audio)
                         and not self.stt_busy and self.segments_dirty)
                if now >= next_boundary or final:
                    self.boundary_sequence += 1
                    self._close_boundary(final)
                    while next_boundary <= now:
                        next_boundary += interval
                self._maybe_complete()
                self.condition.wait(timeout=min(0.05, max(0.001, next_boundary-time.monotonic())))

    def _close_boundary(self, final):
        if not self.segments_dirty:
            self._event('classification_skipped', reason='no_new_or_revised_speech_at_boundary',
                        boundary=self.boundary_sequence, final=final)
            return
        self.segments_dirty = False
        new_id = self.boundary_sequence
        has_new = False
        for item in self.characters:
            index = min(item['start_offset'], len(self.frame_groups)-1)
            if self.frame_groups[index] is None or self.frame_groups[index] == -1:
                self.frame_groups[index] = new_id
                if item['char'].strip():
                    has_new = True
        self.frame_groups = [(new_id if has_new else -1) if group is None else group for group in self.frame_groups]
        revised = {}
        for item in self.characters:
            index = min(item["start_offset"], len(self.frame_groups) - 1)
            bucket = self.frame_groups[index]
            revised.setdefault(bucket, "")
            revised[bucket] += item["char"]
        old = self.segments
        self.segments = {key: {"segment_id": key, "text": value,
                              "version": self.version}
                         for key, value in sorted(revised.items()) if value.strip()}
        new_speech = self.segments.get(new_id,{}).get('text','') if has_new else ''
        self._event('segments_closed', boundary=new_id, final=final, version=self.version,
                    segments=list(self.segments.values()),
                    revised_ids=[k for k in old if k in self.segments and old[k]["text"] != self.segments[k]["text"]],
                    new_ids=[new_id] if has_new else [])
        if not self.segments:
            self._event("classification_skipped", reason="unchanged_or_empty_context")
            return
        if self.approach == "latest" and not new_speech.strip():
            self._event("classification_skipped", reason="revision_only_latest_waits_for_new_speech")
            return
        segments = list(self.segments.values())
        if self.approach == "latest":
            predictive = new_speech
        elif self.approach == "recent":
            predictive = "".join(x["text"] for x in segments[-self.config["recent_segment_count"]:])
        else:
            predictive = self.transcript
        context, omission = self.context_builder(predictive)
        if not context.strip():
            self._event("classification_skipped", reason="empty_assembled_context")
            return
        fingerprint = hashlib.sha256(context.encode()).hexdigest()
        if fingerprint == self.last_context:
            self._event("classification_skipped", reason="context_already_classified")
            return
        if self.pending:
            self._event("classification_skipped", version=self.pending[0], exact_input=self.pending[1],
                        omitted=self.pending[3], reason="superseded_pending_context")
        self.pending = (self.version, context, fingerprint, omission)
        self.condition.notify_all()

    def _prediction_loop(self):
        while True:
            with self.condition:
                self._check_lease()
                if self.state in {"failed", "cancelled", "complete"}:
                    return
                if self.pending is None:
                    self._maybe_complete()
                    self.condition.wait(timeout=0.2)
                    continue
                version, context, fingerprint, omission = self.pending
                self.pending = None
                if fingerprint == self.last_context:
                    continue
                self.classifier_busy = True
                request_id = f"{self.id}:{version}:{uuid.uuid4().hex[:8]}"
                self._event("classification_started", request_id=request_id, version=version,
                            exact_input=context, omitted=omission)
            try:
                response = self.classifier.predict({"request_id": request_id, "transcript": context})
                if response.get('status') == 'success':
                    scores = response.get('probabilities', {})
                    valid = (response.get('request_id') == request_id and set(scores) == {'Scam','Not Scam'}
                             and all(isinstance(x,(int,float)) and math.isfinite(x) and 0<=x<=1 for x in scores.values())
                             and abs(sum(scores.values())-1)<1e-6 and response.get('threshold')==0.5
                             and response.get('label') == ('Scam' if scores['Scam']>=0.5 else 'Not Scam'))
                    if not valid:
                        response={'status':'error','error':{'code':'E_INVALID_OUTPUT','message':'Classifier response failed contract validation'}}
            except Exception:
                response = {"status": "error", "error": {"code": "E_INFERENCE_FAILED", "message": "Classifier unavailable"}}
            with self.condition:
                self.classifier_busy = False
                if self.state in {"cancelled", "failed"}:
                    return
                if response.get("status") != "success":
                    self.error = response.get("error") or {'code':'E_INVALID_OUTPUT','message':'Classifier returned an incomplete error response'}
                    self._event("classification_failure", request_id=request_id, response=response)
                else:
                    self.error = None
                    self.last_context = fingerprint
                    self.prediction = {**response, "transcript_version": version}
                    self.history.append(self.prediction)
                    self.warning = self.warning or response["label"] == "Scam"
                    self._event("classification_completed", response=self.prediction)
                self._maybe_complete()
                self.condition.notify_all()

    def retry(self):
        with self.condition:
            if self.state not in {"active", "finishing"} or not self.error:
                raise ProtocolError("No eligible classification failure")
            # Replay the exact failed request input, never a rewritten context.
            started = next((x for x in reversed(self.events) if x["kind"] == "classification_started"), None)
            if not started:
                raise ProtocolError("No failed classifier request")
            text = started["exact_input"]
            self.pending = (started["version"], text, hashlib.sha256(text.encode()).hexdigest(), started["omitted"])
            self._event("explicit_classifier_retry", original_request_id=started["request_id"])
            self.condition.notify_all()

    def _maybe_complete(self):
        if self.state != "finishing":
            return
        if time.monotonic() - self.finishing_started > self.config["completion_timeout_seconds"]:
            self.fail("E_COMPLETION_TIMEOUT", "Required work did not finish")
        elif (len(self.audio) == self.processed_samples and not self.stt_busy
              and not self.classifier_busy and self.pending is None and not self.segments_dirty):
            if self.error:
                # Keep the exact failed request eligible for explicit retry
                # until the existing completion deadline. Never call it complete.
                return
            elif not self.transcript.strip() or not self.history:
                self.fail('E_EMPTY_TRANSCRIPT', 'No usable classified speech was produced')
            else:
                self.state = "complete"
                self._event("complete", final_sample=len(self.audio))
                self._clear_unsaved()
                self.condition.notify_all()
