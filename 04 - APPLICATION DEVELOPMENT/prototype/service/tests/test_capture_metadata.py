from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import validate_capture_metadata
from core import ProtocolError


class CaptureMetadataTests(unittest.TestCase):
    def setUp(self):
        self.config = {'audio_sample_rate_hz': 16000}

    def test_host_capture_does_not_need_native_conversion_metadata(self):
        validate_capture_metadata({'kind': 'capture_started'}, self.config, 'microphone')
        validate_capture_metadata({'kind': 'playback_started'}, self.config, 'recorded')

    def test_client_cannot_claim_conversion_metadata(self):
        with self.assertRaises(ProtocolError):
            validate_capture_metadata({'capture_sample_rate_hz': 48000}, self.config, 'microphone')

    def test_recorded_mode_cannot_claim_microphone_conversion(self):
        with self.assertRaises(ProtocolError):
            validate_capture_metadata({'conversion': {'method': 'forged'}}, self.config, 'recorded')
