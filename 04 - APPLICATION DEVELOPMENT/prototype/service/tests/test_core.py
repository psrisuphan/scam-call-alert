import array
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Session, ProtocolError

CONFIG = {"stt_window_seconds": 1, "stt_overlap_seconds": 0.2,
          "update_interval_seconds": 0.05, "recent_segment_count": 3,
          "max_queued_audio_seconds": 10, "completion_timeout_seconds": 2}


class Recognizer:
    def __init__(self):
        self.windows = []
    def recognize(self, pcm):
        values = array.array('h'); values.frombytes(pcm)
        ids = list(values[::1600])
        self.windows.append(len(values))
        return {"text": self.decode(ids)[0], "frames": ids,
                "times": [(i + 0.5) / 10 for i in range(len(ids))]}
    def decode(self, ids):
        text, chars, previous = "", [], 0
        for i, token in enumerate(ids):
            if token and token != previous:
                char = chr(96 + token)
                text += char
                chars.append({"char": char, "start_offset": i})
            previous = token
        return text, chars


class Classifier:
    def __init__(self):
        self.inputs = []
        self.block = None
    def predict(self, request):
        self.inputs.append(request)
        if self.block:
            self.block.wait()
        return {"request_id": request['request_id'], "status": "success", "model_version": "fixture",
                "label": "Scam", "probabilities": {"Scam": 0.7, "Not Scam": 0.3}, "threshold":0.5, "error": None}


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.sessions = []
    def tearDown(self):
        for s in self.sessions:
            if s.classifier.block:
                s.classifier.block.set()
            s.cancel(); s.stt_thread.join(2); s.predict_thread.join(2);s.schedule_thread.join(2)
        self.temp.cleanup()
    def session(self, mode='recorded', approach='accumulated', config=None):
        s = Session(config or CONFIG, Recognizer(), Classifier(), lambda x: (x, {}),
                    mode=mode, approach=approach, evidence_root=self.temp.name)
        self.sessions.append(s)
        return s

    def test_closing_terminal_session_preserves_outcome(self):
        for outcome in ('complete', 'failed'):
            s = self.session()
            with s.condition:
                s.state = outcome
            s.cancel()
            self.assertEqual(s.state, outcome)
            self.assertEqual(s.events[-1]['kind'], 'session_closed')
            self.assertEqual(s.events[-1]['final_state'], outcome)
    def pcm(self, tokens):
        return array.array('h', [token for token in tokens for _ in range(1600)]).tobytes()
    def test_microphone_signal_measurements_and_unsaved_cleanup(self):
        s = self.session(mode='microphone')
        pcm = array.array('h', [0, 16384, -16384, 0]).tobytes()
        snapshot = s.accept_audio(0, 0, 4, pcm, 4 / 16)
        self.assertEqual(snapshot['audio_signal']['peak'], 0.5)
        self.assertAlmostEqual(snapshot['audio_signal']['rms'], 0.5 / (2 ** 0.5))
        s.cancel()
        self.assertIsNone(s.snapshot()['audio_signal'])
        self.assertEqual(len(s.audio), 0)
        self.assertFalse(s.directory.exists())
    def test_zero_audio_has_finite_signal_measurements(self):
        s = self.session(mode='microphone')
        signal = s.accept_audio(0, 0, 4, bytes(8), 4 / 16)['audio_signal']
        self.assertEqual(signal, {'peak': 0.0, 'rms': 0.0, 'rms_dbfs': -120.0})
    def feed(self, s, tokens):
        start = len(s.audio); end = start + 1600 * len(tokens)
        return s.accept_audio(s.seq, start, end, self.pcm(tokens), end / 16)
    def wait(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(predicate())
    def test_future_and_missing_ranges_are_rejected(self):
        s = self.session()
        with self.assertRaises(ProtocolError):
            s.accept_audio(0, 0, 1600, self.pcm([1]), 0)
        self.assertEqual(len(s.audio), 0)
        with self.assertRaises(ProtocolError):
            s.accept_audio(1, 0, 1600, self.pcm([1]), 100)
        self.assertEqual(s.state, 'failed')
    def test_exact_network_retry_is_idempotent(self):
        s = self.session(); data = self.pcm([1])
        s.accept_audio(0, 0, 1600, data, 100)
        s.accept_audio(0, 0, 1600, data, 100)
        self.assertEqual(len(s.audio), 1600)
        self.assertEqual(s.seq, 1)
    def test_short_tail_flush_and_repeated_speech(self):
        s = self.session()
        self.feed(s, [1,1,0,1,1,0,2,2,0,2,2,0,3])
        s.finish(); self.wait(lambda: s.state == 'complete')
        self.assertEqual(s.transcript, 'aabbc')
        self.assertEqual(s.recognizer.windows, [16000, 8000])
        self.assertEqual(s.processed_samples, len(s.audio))
    def test_no_overlap_only_final_window(self):
        s = self.session(); self.feed(s, [1] * 10)
        self.wait(lambda: s.processed_samples == 16000)
        s.finish(); self.wait(lambda: s.state == 'complete')
        self.assertEqual(s.recognizer.windows, [16000])
    def test_cancellation_rejects_late_prediction(self):
        s = self.session(); gate = threading.Event(); s.classifier.block = gate
        self.feed(s, [1] * 10); self.wait(lambda: s.classifier_busy)
        s.cancel(); gate.set(); self.wait(lambda: not s.classifier_busy)
        self.assertFalse(s.warning); self.assertIsNone(s.prediction)
    def test_microphone_privacy_and_opt_in(self):
        s = self.session(mode='microphone'); self.feed(s, [1] * 10)
        self.wait(lambda: bool(s.transcript)); s.cancel()
        self.assertFalse(Path(self.temp.name, s.id).exists())
        self.assertEqual(s.transcript, ''); self.assertFalse(s.audio)
        saved = self.session(mode='microphone'); self.feed(saved, [1])
        saved.enable_save(); saved.cancel()
        self.assertEqual(Path(self.temp.name, saved.id, 'audio.pcm').stat().st_size, 3200)
        rows = [json.loads(x) for x in Path(self.temp.name, saved.id, 'events.jsonl').read_text().splitlines()]
        self.assertTrue(any(x['kind'] == 'audio_accepted' for x in rows))
    def test_overload_fails_mic_without_silent_drop(self):
        s = self.session(mode='microphone', config={**CONFIG, 'max_queued_audio_seconds': 0.05})
        with self.assertRaises(ProtocolError): self.feed(s, [1])
        self.assertEqual(s.error['code'], 'E_OVERLOAD')
        self.assertEqual(len(s.audio), 0)
    def test_unsaved_mic_failure_retains_only_non_content_diagnostics(self):
        s = self.session(mode='microphone')
        pcm = array.array('h', [16384, -16384, 0, 0]).tobytes()
        s.accept_audio(0, 0, 4, pcm, 4 / 16)
        s.stt_busy = True
        s.stt_active_window = (0, 80000)
        s.stt_active_started = time.monotonic() - 0.25
        s.fail('E_OVERLOAD', 'Analysis cannot keep up')
        metrics = s.snapshot()['microphone_failure_diagnostics']
        self.assertEqual(metrics['accepted_samples'], 4)
        self.assertEqual(metrics['processed_samples'], 0)
        self.assertEqual(metrics['queued_samples'], 4)
        self.assertEqual(metrics['last_signal_metrics']['peak'], 0.5)
        self.assertEqual(metrics['stt_windows_completed'], 0)
        self.assertAlmostEqual(metrics['active_stt_window']['elapsed_seconds'], 0.25, delta=0.1)
        self.assertEqual(len(s.audio), 0)
        self.assertEqual(s.transcript, '')
        self.assertFalse(any(k in metrics for k in ('pcm', 'audio', 'text', 'transcript', 'frames')))
    def test_empty_audio_not_successful_not_scam(self):
        s = self.session(); s.finish()
        self.assertEqual(s.state, 'failed'); self.assertIsNone(s.prediction)
    def test_saved_snapshot_preserves_counts_after_restart(self):
        s = self.session(); self.feed(s,[1]*10); s.finish()
        self.wait(lambda:s.state=='complete')
        saved=json.loads(Path(self.temp.name,s.id,'snapshot.json').read_text())
        self.assertEqual(saved['state'],'complete')
        self.assertEqual(saved['audio_samples'],16000)
        self.assertEqual(saved['processed_samples'],16000)
    def test_latest_excludes_old_prefix_on_next_boundary(self):
        s=self.session(approach='latest')
        self.feed(s,[1]*10); self.wait(lambda:bool(s.classifier.inputs))
        self.feed(s,[0,2,2,0,3,3,0,4]);s.finish()
        self.wait(lambda:s.state=='complete')
        self.assertGreaterEqual(len(s.classifier.inputs),2)
        self.assertIn('b',s.classifier.inputs[-1]['transcript'])
        self.assertNotIn('a',s.classifier.inputs[-1]['transcript'])
    def test_disconnected_client_fails_and_clears_unsaved_mic(self):
        s=self.session(mode='microphone',config={**CONFIG,'session_lease_seconds':.05})
        self.feed(s,[1])
        self.wait(lambda:s.state=='failed')
        self.assertEqual(s.error['code'],'E_CLIENT_DISCONNECTED')
        self.assertFalse(s.audio)
    def test_revision_only_latest_does_not_create_new_prediction(self):
        s=self.session(approach='latest');self.feed(s,[1]*10)
        self.wait(lambda:len(s.classifier.inputs)==1 and not s.classifier_busy)
        original=s.recognizer.recognize
        def revised(pcm):
            result=original(pcm);result['frames'][:2]=[2,2];return result
        s.recognizer.recognize=revised
        self.feed(s,[0]*8);s.finish();self.wait(lambda:s.state=='complete')
        self.assertEqual(len(s.classifier.inputs),1)
        self.assertTrue(any(x.get('reason')=='revision_only_latest_waits_for_new_speech' for x in s.events))
    def test_scheduling_continues_while_prediction_is_busy(self):
        s=self.session();gate=threading.Event();s.classifier.block=gate
        self.addCleanup(gate.set)
        self.feed(s,[1]*10);self.wait(lambda:s.classifier_busy)
        self.feed(s,[0,2,2,0,2,2,0,0]);self.wait(lambda:len(s.segments)>=2)
        self.feed(s,[0,3,3,0,3,3,0,0]);self.wait(lambda:len(s.segments)>=3)
        self.wait(lambda:any(x.get('reason')=='superseded_pending_context' for x in s.events))
        gate.set();s.finish();self.wait(lambda:s.state=='complete')
    def test_malformed_scores_are_failure_never_not_scam(self):
        s=self.session();s.classifier.predict=lambda request:{'status':'success','probabilities':{'Scam':float('nan'),'Not Scam':0},'request_id':request['request_id']}
        self.feed(s,[1]*10);s.finish();self.wait(lambda:s.state=='failed')
        self.assertFalse(s.warning);self.assertIsNone(s.prediction)
    def test_native_start_signal_precedes_audio_and_clock(self):
        s=self.session(config={**CONFIG,'require_native_start_signal':True})
        with self.assertRaises(ProtocolError):self.feed(s,[1])
        self.assertEqual(len(s.audio),0)
        s.begin_timing(1000);self.feed(s,[1]*10);s.finish()
        self.wait(lambda:s.state=='complete')
        origins=[x for x in s.events if x['kind']=='scheduler_origin']
        self.assertEqual(len(origins),1)
    def test_empty_recognition_is_unavailable_not_success(self):
        s=self.session();self.feed(s,[0]*10);s.finish()
        self.wait(lambda:s.state=='failed')
        self.assertIsNone(s.prediction)
        self.assertEqual(s.error['code'],'E_EMPTY_TRANSCRIPT')

    def test_final_classifier_failure_can_retry_exact_input(self):
        s = self.session()
        original = s.classifier.predict
        attempts = []
        def fail_once(request):
            attempts.append(request['transcript'])
            if len(attempts) == 1:
                return {'status': 'error', 'error': {'code': 'E_TEST', 'message': 'Temporary failure'}}
            return original(request)
        s.classifier.predict = fail_once
        self.feed(s, [1] * 10)
        s.finish()
        self.wait(lambda: bool(s.error))
        self.assertEqual(s.state, 'finishing')
        s.retry()
        self.wait(lambda: s.state == 'complete')
        self.assertEqual(attempts[0], attempts[1])


if __name__ == '__main__': unittest.main()
