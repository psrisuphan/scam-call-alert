import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prepare_fleurs_subset import FleursRecord, parse_metadata, select_records


class PrepareFleursSubsetTests(unittest.TestCase):
    def test_parser_preserves_raw_and_normalized_transcripts(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "dev.tsv"
            path.write_text(
                "42\tclip.wav\tRaw transcript!\tnormalized transcript\tphones\t16000\tFEMALE\n",
                encoding="utf-8",
            )
            record = parse_metadata(path)[0]
        self.assertEqual(record.sentence_id, "42")
        self.assertEqual(record.audio_filename, "clip.wav")
        self.assertEqual(record.raw_transcription, "Raw transcript!")
        self.assertEqual(record.transcription, "normalized transcript")
        self.assertEqual(record.duration_seconds, 1.0)

    def test_selection_is_repeatable_and_reaches_target_with_whole_clips(self):
        records = [
            FleursRecord(str(i), f"{i:02}.wav", "raw", "normalized", "phones", 160_000, "OTHER")
            for i in range(20)
        ]
        first, remaining = select_records(records, target_seconds=90)
        second, _ = select_records(records, target_seconds=90)
        self.assertEqual([r.audio_filename for r in first], [r.audio_filename for r in second])
        self.assertEqual(len(first), 9)
        self.assertEqual(sum(r.duration_seconds for r in first), 90.0)
        self.assertEqual(len(remaining), len(records) - len(first))


if __name__ == "__main__":
    unittest.main()
