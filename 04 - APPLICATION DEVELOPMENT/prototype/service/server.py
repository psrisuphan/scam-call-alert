#!/usr/bin/env python3
"""Loopback-only native-app service. Start explicitly in diagnostic mode.

Recorded session evidence is persisted outside Git. Mic evidence is ephemeral
unless Save is requested. Default HTTP logging never writes transcripts.
"""
import argparse
import csv
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time
from urllib.parse import urlparse, parse_qs
from adapters import ClassifierAdapter, Wav2VecAdapter, file_hash, ROOT
from core import ProtocolError, Session
from prepare_recordings import validate_provenance
from microphone_capture import HostMicrophoneCapture

CODE_IDENTITIES = {name:file_hash(Path(__file__).with_name(name)) for name in ('core.py','adapters.py','server.py','prepare_recordings.py','microphone_capture.py')}


def validate_capture_metadata(data, config, mode):
    keys = {'capture_sample_rate_hz', 'output_sample_rate_hz', 'conversion'}
    if keys & data.keys():
        raise ProtocolError('Host microphone capture does not accept client conversion metadata')


class Application:
    def __init__(self, config, recognizer, classifier, storage, diagnostic=False, recordings=None):
        self.config, self.recognizer, self.classifier = config, recognizer, classifier
        self.diagnostic = diagnostic
        self.storage = Path(storage)
        self.sessions = {}
        self.lock = threading.Lock()
        self.inference_diagnostic_active = False
        # STT and classifier share MPS on the demo host. Serialize complete
        # component calls so classifier cache cleanup cannot race STT inference.
        self.compute_lock = threading.RLock()
        self.recognizer.lock = self.compute_lock
        self.classifier.lock = self.compute_lock
        self.config_id = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        self.recordings = []
        recording_root = Path(recordings) if recordings else self.storage / 'recordings'
        manifest = recording_root / 'audio_manifest.csv'
        if manifest.exists():
            with manifest.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
                validate_provenance(recording_root, rows)
                for row in rows:
                    if row["partition"] != "development" and not (diagnostic and row["partition"] == "diagnostic"):
                        continue
                    # Fidelity approval is independent of classification quality.
                    if row["fidelity_status"] != "verified" and not diagnostic:
                        continue
                    path = (recording_root / row["audio_file"]).resolve()
                    if path.parent != (recording_root / 'audio').resolve():
                        raise ValueError("Invalid recording path")
                    if file_hash(path) != row["audio_sha256"]:
                        raise ValueError("Recording checksum changed")
                    self.recordings.append({"id": row["recording_id"], "title": row["recording_id"] + (" · diagnostic / unverified" if row["fidelity_status"] != "verified" else ""),
                                            "duration_seconds": float(row["duration_seconds"]), "path": path})

    def start(self, data):
        allowed = {"mode", "approach", "save", "recording_id"}
        if not isinstance(data,dict) or ('save' in data and type(data['save']) is not bool):
            raise ProtocolError('Invalid session request')
        if any(file_hash(Path(__file__).with_name(name)) != digest for name,digest in CODE_IDENTITIES.items()):
            raise ProtocolError('Service source changed; restart it before a new session')
        if set(data) - allowed:
            raise ProtocolError("Unexpected session fields")
        with self.lock:
            if self.inference_diagnostic_active:
                raise ProtocolError('A diagnostic inference is currently running')
            if any(s.state in {"active", "finishing"} for s in self.sessions.values()):
                raise ProtocolError("End the current session before starting another")
            for old in self.sessions.values():
                source = getattr(old, 'microphone_source', None)
                if source:
                    source.stop()
            if data.get("mode") == "recorded" and not any(x["id"] == data.get("recording_id") for x in self.recordings):
                raise ProtocolError("Recording is not fidelity-verified development audio")
            session = Session(self.config, self.recognizer, self.classifier, self.classifier.assemble,
                              mode=data.get("mode"), approach=data.get("approach", self.config["context_approach"]),
                              evidence_root=self.storage / "runs", save=data.get("save", False),
                              recording_id=data.get("recording_id"))
            self.sessions[session.id] = session
            if session.mode == 'microphone' and self.config.get('microphone_input_source') == 'mac_coreaudio_direct_host_stt':
                session.microphone_source = HostMicrophoneCapture(session, self.config)
            return session.snapshot()

    def diagnostic_inference_order(self):
        if not self.diagnostic:
            raise ProtocolError('Inference diagnostics require diagnostic mode')
        with self.lock:
            if self.inference_diagnostic_active or any(s.state in {'active', 'finishing'} for s in self.sessions.values()):
                raise ProtocolError('Inference diagnostics cannot run during an active session')
            self.inference_diagnostic_active = True
        try:
            # Identical neutral five-second inputs stay outside any user session.
            pcm = bytes(16000 * 5 * 2)
            input_sha256 = hashlib.sha256(pcm).hexdigest()
            warm_result = self.recognizer.recognize(pcm)
            warm = warm_result.get('resources', {})
            classifier_started = time.perf_counter()
            prediction = self.classifier.predict({'request_id': 'diagnostic-resource-warmup',
                                                  'transcript': 'neutral diagnostic warmup'})
            classifier_seconds = time.perf_counter() - classifier_started
            cache_cleanup = getattr(self.classifier, 'last_cache_cleanup', {})
            after_cleanup_result = self.recognizer.recognize(pcm)
            after_cleanup = after_cleanup_result.get('resources', {})
            def safe_resources(value):
                allowed = ('processing_seconds', 'lock_wait_seconds', 'preprocessing_seconds',
                           'forward_dispatch_seconds', 'forward_sync_copy_seconds', 'decode_seconds',
                           'process_rss_bytes', 'mps_driver_allocated_bytes', 'mps_current_allocated_bytes')
                return {key: value[key] for key in allowed if key in value}
            return {'input': {'sample_rate_hz': 16000, 'channels': 1, 'samples': 80000,
                              'kind': 'generated_silence', 'saved': False,
                              'sha256': input_sha256},
                    'stt_before_classifier': safe_resources(warm),
                    'classifier': {'elapsed_seconds': classifier_seconds,
                                   'status': prediction.get('status'),
                                   'model_version': self.classifier.version,
                                   **cache_cleanup},
                    'stt_after_cleanup': safe_resources(after_cleanup),
                    'same_input_and_output': {
                        'input_sha256_matches': input_sha256 == hashlib.sha256(pcm).hexdigest(),
                        'ctc_output_sha256_matches': hashlib.sha256(json.dumps(warm_result.get('frames', []), separators=(',', ':')).encode()).hexdigest()
                            == hashlib.sha256(json.dumps(after_cleanup_result.get('frames', []), separators=(',', ':')).encode()).hexdigest(),
                    }}
        finally:
            with self.lock:
                self.inference_diagnostic_active = False


class Handler(BaseHTTPRequestHandler):
    # The emulator's network takes ~0.5 s to finish each connection close, which throttled the
    # native poll loop (timer/transcript updates). Keep-alive reuses one connection instead.
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True

    def log_message(self, *args):
        pass

    def respond(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def dispatch(self):
        app = self.server.application
        path = urlparse(self.path)
        parts = path.path.strip("/").split("/")
        if self.command == "GET" and parts == ["health"]:
            diagnostics = []
            capture_status = []
            mic_failures = []
            if app.diagnostic:
                with app.lock:
                    snapshots = [session.snapshot() for session in app.sessions.values()]
                diagnostics = [{"audio_samples": s["audio_samples"], "processed_samples": s["processed_samples"],
                                "audio_signal": s["audio_signal"], "transcript_characters": len(s["transcript"]),
                                "stt_busy": s["stt_busy"], "error": s["error"],
                                "prediction_label": s["prediction"]["label"] if s["prediction"] else None,
                                "microphone_capture": s["microphone_capture"]}
                               for s in snapshots if s["mode"] == "microphone" and s["state"] in {"active", "finishing"}]
                capture_status = [s['microphone_capture'] for s in snapshots if s['microphone_capture']]
                mic_failures = [{'session_id': s['session_id'], 'error': s['error'],
                                 'diagnostics': s['microphone_failure_diagnostics']}
                                for s in snapshots if s['mode'] == 'microphone' and s['state'] == 'failed'
                                and s.get('microphone_failure_diagnostics')]
            return self.respond({"status": "ready", "model_kind": app.classifier.kind,
                                 "model_version": app.classifier.version, "stt_revision": app.recognizer.version,
                                 "configuration_id": app.config_id, "configuration": app.config,
                                 "microphone_diagnostics": diagnostics, "microphone_captures": capture_status,
                                 "microphone_failures": mic_failures})
        if self.command == "GET" and parts == ["recordings"]:
            return self.respond([{k: v for k, v in row.items() if k != "path"} for row in app.recordings])
        if self.command == "GET" and len(parts) == 2 and parts[0] == "recordings":
            row = next((x for x in app.recordings if x["id"] == parts[1]), None)
            if not row:
                raise ProtocolError("Recording not found")
            body = row["path"].read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > 2_000_000:
            raise ProtocolError("Request body exceeds limit")
        raw = self.rfile.read(length) if self.command == "POST" else b""
        if self.command == "POST" and parts == ["diagnostics", "inference-order"]:
            if raw:
                raise ProtocolError('Inference diagnostic does not accept a request body')
            return self.respond(app.diagnostic_inference_order())
        if self.command == "POST" and parts == ["sessions"]:
            return self.respond(app.start(json.loads(raw)), 201)
        if len(parts) == 2 and parts[0] == 'sessions' and parts[1] not in app.sessions and self.command == 'GET':
            if len(parts[1]) == 32 and all(x in '0123456789abcdef' for x in parts[1]):
                saved = app.storage / 'runs' / parts[1] / 'snapshot.json'
                if saved.exists():
                    value = json.loads(saved.read_text())
                    if value['state'] in {'active', 'finishing'}:
                        value['state'] = 'failed'
                        value['error'] = {'code':'E_SERVICE_RESTART', 'message':'Previous host run was interrupted; original evidence preserved'}
                    return self.respond(value)
        if len(parts) < 2 or parts[0] != "sessions" or parts[1] not in app.sessions:
            raise ProtocolError("Session not found")
        session = app.sessions[parts[1]]
        session.touch()
        if self.command == "GET" and len(parts) == 2:
            return self.respond(session.snapshot())
        if self.command != "POST" or len(parts) != 3:
            raise ProtocolError("Unknown route")
        action = parts[2]
        if action == "audio":
            if session.mode == 'microphone' and app.config.get('microphone_input_source') == 'mac_coreaudio_direct_host_stt':
                raise ProtocolError('Microphone audio is accepted only from the session-bound host capture')
            query = parse_qs(path.query, strict_parsing=True)
            if set(query) != {"seq", "start", "end", "available_ms", "available_monotonic_ms"}:
                raise ProtocolError("Invalid audio metadata")
            result = session.accept_audio(int(query["seq"][0]), int(query["start"][0]),
                                          int(query["end"][0]), raw, float(query["available_ms"][0]),
                                          float(query['available_monotonic_ms'][0]))
            return self.respond(result)
        if action == "finish":
            return self.respond(session.finish())
        if action == "cancel":
            session.cancel()
            source = getattr(session, 'microphone_source', None)
            if source:
                source.stop()
        elif action == "save":
            session.enable_save()
        elif action == "retry":
            session.retry()
        elif action == "interrupt":
            data = json.loads(raw)
            if set(data) != {"code", "message"}:
                raise ProtocolError("Invalid interruption evidence")
            session.fail(data["code"], data["message"])
            source = getattr(session, 'microphone_source', None)
            if source:
                source.stop()
        elif action == "events":
            data = json.loads(raw)
            allowed = {"kind", "client_elapsed_ms", "client_monotonic_ms", "timing_origin_ms", "audio_position_ms", "condition", "notification_id", "display_observed", "process_pss_bytes", "process_cpu_time_ms", "capture_sample_rate_hz", "output_sample_rate_hz", "conversion"}
            if set(data) - allowed or not isinstance(data.get("kind"), str):
                raise ProtocolError("Invalid client evidence")
            validate_capture_metadata(data, app.config, session.mode)
            if data['kind'] == 'capture_started':
                origin = data.get('timing_origin_ms')
                if not isinstance(origin, (int, float)) or origin < 0:
                    raise ProtocolError('Invalid native timing origin')
                source = getattr(session, 'microphone_source', None)
                if source:
                    if source.worker is not None:
                        raise ProtocolError('Duplicate microphone source activation')
                    try:
                        session.begin_timing(origin_source='host_monotonic')
                        source.start()
                    except Exception:
                        if session.state == 'active':
                            session.fail('E_MICROPHONE_CAPTURE', 'Live Mac microphone capture could not start')
                        source.stop()
                        raise ProtocolError('Live Mac microphone capture could not start')
                    if session.state != 'active':
                        source.stop()
                        raise ProtocolError('Microphone session ended during startup')
                    with session.lock:
                        session._event('microphone_capture_started', source=app.config['microphone_capture'], clock='host_monotonic')
            with session.lock:
                if data['kind'] in {'playback_started','capture_started'}:
                    if session.mode != 'microphone':
                        session.begin_timing(data['timing_origin_ms'])
                session._event("client_observation", client_kind=data.pop("kind"), **data)
        else:
            raise ProtocolError("Unknown session action")
        return self.respond(session.snapshot())

    def do_GET(self):
        self.safe_dispatch()

    def do_POST(self):
        self.safe_dispatch()

    def safe_dispatch(self):
        try:
            self.connection.settimeout(self.server.application.config['request_timeout_seconds'])
            self.dispatch()
        except (ProtocolError, ValueError, KeyError, json.JSONDecodeError) as exc:
            self.respond({"error": {"code": "E_PROTOCOL", "message": str(exc)}}, 409)
        except Exception:
            self.respond({"error": {"code": "E_SERVICE", "message": "Service execution failed"}}, 500)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--model-kind", required=True, choices=("interim", "official"))
    parser.add_argument("--classifier-device", default="cpu")
    parser.add_argument("--stt-cache", required=True, type=Path)
    parser.add_argument("--storage", required=True, type=Path)
    parser.add_argument("--recordings", type=Path)
    parser.add_argument("--config", type=Path, default=Path(__file__).parents[1] / "integration_config.json")
    parser.add_argument("--diagnostic", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if not args.diagnostic and (config["approval_status"] != "owner_confirmed" or args.model_kind != "official"):
        parser.error("Formal runs require confirmed settings and the official model")
    if not 0 <= config["stt_overlap_seconds"] < config["stt_window_seconds"]:
        parser.error("Invalid STT overlap")
    startup_started = time.perf_counter()
    recognizer = Wav2VecAdapter(args.stt_cache)
    classifier = ClassifierAdapter(args.bundle, args.model_kind, args.classifier_device)
    # Untimed neutral component warmup prevents MPS shader/weight page-in work
    # from masquerading as live recognition latency. No datasets are consulted.
    recognizer.recognize(bytes(16000 * 5 * 2))
    warmup = classifier.predict({'request_id':'startup-warmup','transcript':'สวัสดี'})
    if warmup.get('status') != 'success':
        raise RuntimeError('Classifier warmup failed; service is not ready')
    config['component_identities'] = {'model_kind':args.model_kind,'model_version':classifier.version,
        'stt_revision':recognizer.version,
        'classifier_device':str(classifier.device),
        'stt_device':str(getattr(recognizer.asr, 'device', 'unknown')),
        'source_sha256':CODE_IDENTITIES}
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.application = Application(config, recognizer, classifier, args.storage, args.diagnostic, args.recordings)
    print(json.dumps({"status": "ready", "port": args.port, "model_kind": args.model_kind,
                      "model_version": classifier.version, 'startup_load_and_warmup_seconds':time.perf_counter()-startup_started}, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for session in server.application.sessions.values():
            session.cancel()
            source = getattr(session, 'microphone_source', None)
            if source:
                source.stop()
        server.server_close()


if __name__ == "__main__":
    main()
