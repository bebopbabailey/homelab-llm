import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "audit_studio_scheduling.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("audit_studio_scheduling_module", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(audit)


class AuditStudioSchedulingTests(unittest.TestCase):
    def test_runtime_ok_accepts_direct_launchd_ancestry(self):
        runtime = {
            "listener_pid": "31765",
            "is_vllm_listener": True,
            "under_mlx_launch": False,
            "under_launchd": True,
        }
        self.assertTrue(audit._runtime_8100_ok(runtime))

    def test_runtime_ok_accepts_legacy_mlx_launch_ancestry(self):
        runtime = {
            "listener_pid": "31765",
            "is_vllm_listener": True,
            "under_mlx_launch": True,
            "under_launchd": False,
        }
        self.assertTrue(audit._runtime_8100_ok(runtime))

    def test_runtime_ok_rejects_non_vllm_listener(self):
        runtime = {
            "listener_pid": "31765",
            "is_vllm_listener": False,
            "under_mlx_launch": False,
            "under_launchd": True,
        }
        self.assertFalse(audit._runtime_8100_ok(runtime))


if __name__ == "__main__":
    unittest.main()
