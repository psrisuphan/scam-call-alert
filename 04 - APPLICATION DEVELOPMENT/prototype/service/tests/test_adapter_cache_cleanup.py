import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters import ClassifierAdapter


class CacheCleanupTests(unittest.TestCase):
    def test_retired_provisional_app_adapter_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "interim or official"):
            ClassifierAdapter(None, "provisional", "cpu")

    def test_mps_cache_release_runs_inside_classifier_lock_and_preserves_result(self):
        order = []

        class Model:
            def predict(self, request):
                self.assert_lock_held()
                order.append('predict')
                return {'status': 'success', 'opaque_result': 7}

            def assert_lock_held(self):
                if adapter.lock.acquire(blocking=False):
                    adapter.lock.release()
                    raise AssertionError('shared inference lock was not held')

        class MPS:
            def driver_allocated_memory(self):
                return 1000 if order.count('empty_cache') == 0 else 400

            def current_allocated_memory(self):
                return 300

            def synchronize(self):
                self.assert_lock_held()
                order.append('synchronize')

            def empty_cache(self):
                self.assert_lock_held()
                order.append('empty_cache')

            @staticmethod
            def assert_lock_held():
                if adapter.lock.acquire(blocking=False):
                    adapter.lock.release()
                    raise AssertionError('shared inference lock was not held')

        adapter = ClassifierAdapter.__new__(ClassifierAdapter)
        adapter.lock = threading.Lock()
        adapter.device = 'mps'
        adapter.model = Model()
        adapter.last_cache_cleanup = {}
        with patch.dict(sys.modules, {'torch': SimpleNamespace(mps=MPS())}):
            result = adapter.predict({'request_id': 'test'})

        self.assertEqual(result, {'status': 'success', 'opaque_result': 7})
        self.assertEqual(order, ['predict', 'synchronize', 'empty_cache'])
        self.assertEqual(adapter.last_cache_cleanup['mps_driver_allocated_bytes_after_cleanup'], 400)
        self.assertEqual(adapter.last_cache_cleanup['mps_current_allocated_bytes_after_cleanup'], 300)

    def test_cpu_classifier_skips_mps_cache_cleanup(self):
        adapter = ClassifierAdapter.__new__(ClassifierAdapter)
        adapter.lock = threading.Lock()
        adapter.device = 'cpu'
        adapter.model = SimpleNamespace(predict=lambda request: {'status': 'success'})
        adapter.last_cache_cleanup = {}
        self.assertEqual(adapter.predict({'request_id': 'test'}), {'status': 'success'})
        self.assertEqual(adapter.last_cache_cleanup, {'cache_cleanup': 'not_applicable'})


if __name__ == '__main__':
    unittest.main()
