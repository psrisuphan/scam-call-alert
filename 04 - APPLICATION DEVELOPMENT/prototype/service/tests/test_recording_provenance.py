import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from prepare_recordings import hash_file, validate_provenance


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        script = self.root / 'scripts/development-00.txt'
        script.write_text('ข้อความทดสอบ', encoding='utf-8')
        self.row = dict(recording_id='development-00', partition='development',
                        sample_id='train-1', source_dataset='primary', label='Scam',
                        group_id='group-1', script_sha256=hash_file(script))
        self.source = dict(sample_id='train-1', source_dataset='primary', label='Scam')
        self.mock = patch('prepare_recordings.selected', return_value=[(self.source, 'group-1', 'ข้อความทดสอบ')])
        self.mock.start()

    def tearDown(self):
        self.mock.stop()
        self.temp.cleanup()

    def test_valid_shared_script(self):
        validate_provenance(self.root, [self.row])

    def test_rejects_membership_metadata_and_duplicate_ids(self):
        for field in ('sample_id', 'source_dataset', 'label', 'group_id', 'script_sha256'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_provenance(self.root, [dict(self.row, **{field: 'wrong'})])
        with self.assertRaises(ValueError):
            validate_provenance(self.root, [self.row, self.row])

    def test_forged_hash_cannot_hide_script_change(self):
        script = self.root / 'scripts/development-00.txt'
        script.write_text('แก้ไขข้อความ', encoding='utf-8')
        with self.assertRaises(ValueError):
            validate_provenance(self.root, [dict(self.row, script_sha256=hash_file(script))])

    def test_final_partition_rejected_before_reading(self):
        with self.assertRaisesRegex(ValueError, 'final-evaluation'):
            validate_provenance(self.root, [dict(partition='test')])

    def test_diagnostic_requires_independent_unlabeled_provenance(self):
        row = dict(self.row, partition='diagnostic', sample_id='', group_id='', label='', source_dataset='independent_synthetic')
        validate_provenance(self.root, [row])
        with self.assertRaises(ValueError):
            validate_provenance(self.root, [dict(row, label='Scam')])


if __name__ == '__main__':
    unittest.main()
