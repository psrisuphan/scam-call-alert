import tempfile
import unittest
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Session
from server import Application, ProtocolError


class Recognizer:
    version = 'test-stt'

    def __init__(self, order):
        self.order = order
        self.inputs = []

    def recognize(self, pcm):
        self.inputs.append(pcm)
        self.order.append('stt')
        return {'text': 'must not escape', 'frames': [7], 'times': [0.1],
                'resources': {'processing_seconds': 0.1, 'lock_wait_seconds': 0.001,
                              'preprocessing_seconds': 0.01, 'forward_dispatch_seconds': 0.02,
                              'forward_sync_copy_seconds': 0.06, 'decode_seconds': 0.009,
                              'process_rss_bytes': 123, 'mps_driver_allocated_bytes': 456}}


class Classifier:
    version = 'test-classifier'

    def __init__(self, order):
        self.order = order
        self.requests = []
        self.last_cache_cleanup = {'cache_cleanup': 'test'}

    def predict(self, request):
        self.requests.append(request)
        self.order.append('classifier')
        return {'status': 'success', 'label': 'Scam'}


class DiagnosticInferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.order = []
        self.recognizer = Recognizer(self.order)
        self.classifier = Classifier(self.order)
        self.app = Application({}, self.recognizer, self.classifier,
                               Path(self.temp.name) / 'storage', diagnostic=True,
                               recordings=Path(self.temp.name) / 'recordings')

    def tearDown(self):
        self.temp.cleanup()

    def test_same_shape_neutral_stt_brackets_classifier_without_content_output(self):
        mps = SimpleNamespace(driver_allocated_memory=lambda: 456,
                              current_allocated_memory=lambda: 123,
                              synchronize=lambda: None, empty_cache=lambda: None)
        with patch.dict(sys.modules, {'torch': SimpleNamespace(mps=mps)}):
            result = self.app.diagnostic_inference_order()
        self.assertEqual(self.order, ['stt', 'classifier', 'stt'])
        self.assertEqual([len(pcm) for pcm in self.recognizer.inputs], [160000] * 2)
        self.assertTrue(all(not any(pcm) for pcm in self.recognizer.inputs))
        self.assertEqual({k: v for k, v in result['input'].items() if k != 'sha256'},
                         {'sample_rate_hz': 16000, 'channels': 1,
                          'samples': 80000, 'kind': 'generated_silence', 'saved': False})
        self.assertEqual(result['stt_before_classifier']['forward_sync_copy_seconds'], 0.06)
        self.assertEqual(result['stt_after_cleanup']['forward_sync_copy_seconds'], 0.06)
        self.assertTrue(result['same_input_and_output']['input_sha256_matches'])
        self.assertTrue(result['same_input_and_output']['ctc_output_sha256_matches'])
        self.assertEqual(result['classifier']['cache_cleanup'], 'test')
        self.assertNotIn('text', str(result))
        self.assertNotIn('frames', str(result))
        self.assertNotIn('label', result['classifier'])

    def test_diagnostic_refuses_to_run_while_session_is_active(self):
        session = Session({'stt_window_seconds': 5, 'stt_overlap_seconds': 1,
                           'update_interval_seconds': 4, 'recent_segment_count': 3,
                           'max_queued_audio_seconds': 20, 'completion_timeout_seconds': 120},
                          self.recognizer, self.classifier, lambda x: (x, {}),
                          mode='microphone', approach='accumulated', evidence_root=self.temp.name)
        self.app.sessions[session.id] = session
        with self.assertRaises(ProtocolError):
            self.app.diagnostic_inference_order()
        session.cancel()
        session.stt_thread.join(1)
        session.predict_thread.join(1)
        session.schedule_thread.join(1)

    def test_session_start_is_blocked_during_diagnostic_inference(self):
        self.app.inference_diagnostic_active = True
        with self.assertRaises(ProtocolError):
            self.app.start({'mode': 'microphone', 'approach': 'accumulated'})
        self.assertEqual(self.app.sessions, {})


if __name__ == '__main__':
    unittest.main()
