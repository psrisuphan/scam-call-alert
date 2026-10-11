import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from score_stt_results import common_clip_scores, edit_counts, normalize_for_cer, score_rows


class ScoreSttResultsTests(unittest.TestCase):
    def test_normalization_matches_plan_without_losing_thai_marks_or_digits(self):
        self.assertEqual(normalize_for_cer(" A, ก้ า 12! "), "aก้า12")

    def test_character_edit_counts(self):
        self.assertEqual(edit_counts("abc", "axc!"), (1, 0, 1))
        self.assertEqual(edit_counts("abc", "ac"), (0, 1, 0))
        self.assertEqual(edit_counts("ac", "abc"), (0, 0, 1))

    def test_corpus_cer_uses_summed_errors_and_reference_characters(self):
        rows = [
            {
                "candidate_id": "candidate-a", "repetition": 1, "clip_id": "a.wav",
                "status": "success", "reference_raw_transcription": "ab",
                "hypothesis_raw_transcription": "ax", "audio_duration_seconds": 2,
                "audio_read_seconds": 0.1, "processing_seconds": 1.0,
            },
            {
                "candidate_id": "candidate-a", "repetition": 1, "clip_id": "b.wav",
                "status": "success", "reference_raw_transcription": "abcd",
                "hypothesis_raw_transcription": "abcd", "audio_duration_seconds": 4,
                "audio_read_seconds": 0.2, "processing_seconds": 2.0,
            },
        ]
        per_clip, aggregates = score_rows(rows, {"a.wav", "b.wav", "missing.wav"})
        self.assertEqual(len(per_clip), 2)
        summary = aggregates[0]
        self.assertEqual(summary["reference_characters"], 6)
        self.assertEqual(summary["total_errors"], 1)
        self.assertAlmostEqual(summary["corpus_cer"], 1 / 6)
        self.assertEqual(summary["missing_clips"], 1)
        self.assertEqual(summary["successful_path_rtf"], 0.5)

    def test_successful_empty_hypothesis_counts_deletions(self):
        row = {
            "candidate_id": "candidate-a", "repetition": 1, "clip_id": "a.wav",
            "status": "success", "reference_raw_transcription": "กข",
            "hypothesis_raw_transcription": "", "audio_duration_seconds": 3,
            "audio_read_seconds": 0, "processing_seconds": 1,
        }
        _, aggregates = score_rows([row], {"a.wav"})
        self.assertEqual(aggregates[0]["deletions"], 2)
        self.assertEqual(aggregates[0]["corpus_cer"], 1.0)

    def test_failures_are_not_assigned_fake_hypotheses(self):
        row = {
            "candidate_id": "candidate-a", "repetition": 1, "clip_id": "a.wav",
            "status": "failure", "error": "out of memory", "audio_duration_seconds": 3,
            "audio_read_seconds": 0.1, "processing_seconds": 2,
        }
        per_clip, aggregates = score_rows([row], {"a.wav"})
        self.assertEqual(per_clip[0]["status"], "failure")
        self.assertEqual(aggregates[0]["failed_clips"], 1)
        self.assertEqual(aggregates[0]["scored_clips"], 0)
        self.assertEqual(aggregates[0]["corpus_cer"], "")

    def test_rtf_excludes_failed_attempts_and_common_clip_metrics_report_coverage(self):
        rows = [
            {
                "candidate_id": "a", "repetition": 1, "clip_id": "same.wav",
                "status": "success", "reference_raw_transcription": "กข",
                "hypothesis_raw_transcription": "กข", "audio_duration_seconds": 2,
                "audio_read_seconds": 0.1, "processing_seconds": 1,
            },
            {
                "candidate_id": "a", "repetition": 1, "clip_id": "other.wav",
                "status": "failure", "error": "oom", "audio_duration_seconds": 10,
                "audio_read_seconds": 0.1, "processing_seconds": 100,
            },
            {
                "candidate_id": "b", "repetition": 1, "clip_id": "same.wav",
                "status": "success", "reference_raw_transcription": "กข",
                "hypothesis_raw_transcription": "กขค", "audio_duration_seconds": 2,
                "audio_read_seconds": 0.1, "processing_seconds": 3,
            },
        ]
        _, aggregates = score_rows(rows, {"same.wav", "other.wav"})
        aggregate_a = next(row for row in aggregates if row["candidate_id"] == "a")
        self.assertEqual(aggregate_a["successful_path_rtf"], 0.5)
        self.assertEqual(aggregate_a["failed_processing_seconds"], 100)
        common = common_clip_scores(rows, expected_clip_count=2)
        self.assertEqual(common[0]["common_scored_clips"], 1)
        self.assertEqual(common[0]["coverage"], 0.5)


if __name__ == "__main__":
    unittest.main()
