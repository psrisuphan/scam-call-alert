import sys
import threading
import time
import types
import unittest
from unittest.mock import patch
import numpy as np

from microphone_capture import HostMicrophoneCapture


class FakeSession:
    state = 'active'

    def __init__(self):
        self.audio = []
        self.failed = None
        self.block = None
        self.accepted_event = threading.Event()

    def accept_audio(self, seq, start, end, pcm, available_ms, available_monotonic_ms, availability_clock=None):
        if self.block:
            self.block.wait(2)
        self.audio.append((seq, start, end, pcm, available_ms, available_monotonic_ms))
        self.accepted_event.set()

    def fail(self, code, message):
        self.failed = (code, message)
        self.state = 'failed'


class FakeStream:
    def __init__(self, callback, *, fail_start=False):
        self.callback = callback
        self.fail_start = fail_start
        self.closed = False

    def start(self):
        if self.fail_start:
            raise PermissionError('denied')
        self.callback(np.ones((1600, 1), dtype=np.int16), 1600, None, None)

    def stop(self):
        pass

    def close(self):
        self.closed = True


def fake_sounddevice(streams, *, fail_check=False):
    module = types.SimpleNamespace(
        query_devices=lambda: [{'name': 'MacBook Air Microphone', 'max_input_channels': 1}],
        CoreAudioSettings=lambda **kwargs: kwargs,
        check_input_settings=lambda **kwargs: (_ for _ in ()).throw(PermissionError('denied')) if fail_check else None,
    )
    def create_stream(**kwargs):
        stream = FakeStream(kwargs['callback'])
        streams.append(stream)
        return stream
    module.InputStream = create_stream
    return module


class HostMicrophoneCaptureTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            'microphone_capture': {'device': 'MacBook Air Microphone', 'sample_rate_hz': 16000,
                                   'block_samples': 1600, 'coreaudio_change_device_parameters': False,
                                   'coreaudio_conversion_quality': 'max'},
            'max_queued_audio_seconds': 2, 'request_timeout_seconds': 1,
        }

    def test_stream_closes_on_stop_and_emits_ordered_pcm(self):
        session, streams = FakeSession(), []
        with patch.dict(sys.modules, {'sounddevice': fake_sounddevice(streams)}):
            source = HostMicrophoneCapture(session, self.config)
            source.start()
            self.assertTrue(session.accepted_event.wait(2))
            source.stop()
        self.assertEqual([(row[0], row[1], row[2]) for row in session.audio], [(0, 0, 1600)])
        self.assertEqual(len(session.audio[0][3]), 3200)
        self.assertTrue(streams[0].closed)
        self.assertFalse(source.snapshot()['active'])

    def test_stop_discards_queued_pcm_after_session_cancel(self):
        session, streams = FakeSession(), []
        with patch.dict(sys.modules, {'sounddevice': fake_sounddevice(streams)}):
            source = HostMicrophoneCapture(session, self.config)
            source.start()
            session.state = 'cancelled'
            source.packets.put_nowait((source.origin_ns, b'\x01\x00' * 1600))
            source.stop()
        self.assertEqual(session.audio, [])
        self.assertEqual(source.packets.qsize(), 0)
        self.assertFalse(source.snapshot()['worker_alive'])

    def test_capture_permission_failure_does_not_leave_stream(self):
        session, streams = FakeSession(), []
        with patch.dict(sys.modules, {'sounddevice': fake_sounddevice(streams, fail_check=True)}):
            source = HostMicrophoneCapture(session, self.config)
            with self.assertRaises(PermissionError):
                source.start()
            source.stop()
        self.assertEqual(streams, [])

    def test_callback_failure_fails_session_and_closes_stream(self):
        session, streams = FakeSession(), []
        module = fake_sounddevice(streams)
        def create_stream(**kwargs):
            stream = FakeStream(kwargs['callback'])
            streams.append(stream)
            original = stream.start
            def start():
                original()
                kwargs['callback'](np.zeros((1600, 1), dtype='int16'), 1600, None, 'input overflow')
            stream.start = start
            return stream
        module.InputStream = create_stream
        with patch.dict(sys.modules, {'sounddevice': module}):
            source = HostMicrophoneCapture(session, self.config)
            with self.assertRaises(RuntimeError):
                source.start()
        self.assertEqual(session.failed[0], 'E_MICROPHONE_CAPTURE')
        self.assertEqual(session.state, 'failed')
        self.assertTrue(streams[0].closed)


if __name__ == '__main__':
    unittest.main()
