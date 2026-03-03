import argparse
import contextlib
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "mlxctl"
LOADER = importlib.machinery.SourceFileLoader("mlxctl_module_runtime", str(MODULE_PATH))
SPEC = importlib.util.spec_from_loader("mlxctl_module_runtime", LOADER)
mlxctl = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mlxctl)


class _FakeResult:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class MlxctlRuntimeHealthTests(unittest.TestCase):
    def setUp(self):
        self._orig = {}

    def _patch(self, name, value):
        self._orig[name] = getattr(mlxctl, name)
        setattr(mlxctl, name, value)

    def tearDown(self):
        for name, value in self._orig.items():
            setattr(mlxctl, name, value)

    def test_status_checks_includes_http_models_ok(self):
        data = {
            "models": {
                "mlx-gpt-oss-120b-mxfp4-q4": {
                    "model_id": "mlx-gpt-oss-120b-mxfp4-q4",
                    "cache_path": "/tmp/model",
                    "port": 8100,
                }
            }
        }

        self._patch("_registry_path", lambda: Path("/tmp/registry.json"))
        self._patch("_load_registry", lambda _path: data)
        self._patch("_port_listening", lambda port: [])
        self._patch("_mlx_pids_for_port", lambda port: [123] if port == 8100 else [])
        self._patch("_mlx_runtime_command_for_port", lambda port: "vllm serve /tmp/model --port 8100" if port == 8100 else None)
        self._patch("_mlx_process_family", lambda _cmd: "vllm-metal")
        self._patch("_runtime_model_path_from_command", lambda _cmd: "/tmp/model")
        self._patch("_launchctl_disabled_map", lambda: {})
        self._patch("_lane_launchd_state", lambda _port, disabled_map=None: {"label": "com.bebop.mlx-lane.8100", "loaded": True, "disabled": False})
        self._patch("_models_endpoint_ok", lambda port, timeout=2: port == 8100)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            mlxctl.cmd_status(argparse.Namespace(checks=True, json=True, table=False))

        payload = json.loads(out.getvalue())
        row_8100 = next(row for row in payload["ports"] if row["port"] == 8100)
        row_8103 = next(row for row in payload["ports"] if row["port"] == 8103)
        self.assertEqual(row_8100["http_models_ok"], True)
        self.assertIsNone(row_8103["http_models_ok"])

    def test_repair_lanes_apply_records_step_results(self):
        data = {
            "models": {
                "mlx-gpt-oss-120b-mxfp4-q4": {
                    "model_id": "mlx-gpt-oss-120b-mxfp4-q4",
                    "port": 8100,
                }
            }
        }

        calls = []

        def fake_sudo(_host, command, check=False, input_bytes=None):
            del check, input_bytes
            calls.append(command)
            return _FakeResult(returncode=0, stdout=b"ok", stderr=b"")

        self._patch("_registry_path", lambda: Path("/tmp/registry.json"))
        self._patch("_load_registry", lambda _path: data)
        self._patch("_is_local_host", lambda: True)
        self._patch("_launchctl_disabled_map", lambda: {"com.bebop.mlx-lane.8100": True})
        self._patch("_lane_launchd_state", lambda _port, disabled_map=None: {"label": "com.bebop.mlx-lane.8100", "loaded": False, "disabled": True})
        self._patch("_port_listening", lambda _port: [])
        self._patch("_mlx_pids_for_port", lambda _port: [])
        self._patch("_studio_sudo_cmd", fake_sudo)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            mlxctl.cmd_repair_lanes(argparse.Namespace(ports="", apply=True, json=True))

        payload = json.loads(out.getvalue())
        self.assertEqual(payload["repair_count"], 1)
        repair = payload["repairs"][0]
        self.assertEqual(repair["port"], 8100)
        self.assertIn("apply_result", repair)
        self.assertTrue(repair["apply_result"]["success"])
        self.assertGreaterEqual(len(repair["apply_result"]["steps"]), 4)
        self.assertTrue(any("launchctl bootstrap" in cmd for cmd in calls))


if __name__ == "__main__":
    unittest.main()
