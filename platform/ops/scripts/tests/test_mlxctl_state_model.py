import argparse
import contextlib
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "mlxctl"
LOADER = importlib.machinery.SourceFileLoader("mlxctl_module_state", str(MODULE_PATH))
SPEC = importlib.util.spec_from_loader("mlxctl_module_state", LOADER)
mlxctl = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mlxctl)


class MlxctlStateModelTests(unittest.TestCase):
    def test_load_registry_migrates_v1_to_lane_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "registry.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "models": {
                            "mlx-gpt-oss-20b-mxfp4-q4": {
                                "model_id": "mlx-gpt-oss-20b-mxfp4-q4",
                                "repo_id": "mlx-community/gpt-oss-20b-MXFP4-Q4",
                                "cache_path": "/tmp/model",
                                "port": 8102,
                            }
                        },
                    }
                )
            )
            payload = mlxctl._load_registry(path)
            self.assertEqual(payload["version"], mlxctl.REGISTRY_VERSION)
            lane = payload["lanes"]["8102"]
            self.assertEqual(lane["desired_target"]["target_slug"], "mlx-gpt-oss-20b-mxfp4-q4")
            self.assertEqual(lane["actual_serving_target"]["target_slug"], "mlx-gpt-oss-20b-mxfp4-q4")

    def test_status_json_includes_desired_and_actual_targets(self):
        data = {
            "version": 2,
            "models": {
                "mlx-llama-3-3-70b-4bit-instruct": {
                    "model_id": "mlx-llama-3-3-70b-4bit-instruct",
                    "cache_path": "/tmp/model",
                    "port": 8101,
                }
            },
            "lanes": {
                "8101": {
                    "port": 8101,
                    "desired_target": {
                        "target_slug": "mlx-llama-3-3-70b-4bit-instruct",
                        "repo_id": "mlx-community/Llama-3.3-70B-Instruct-4bit",
                        "expected_served_model_identity": "mlx-llama-3-3-70b-4bit-instruct",
                    },
                    "actual_serving_target": {
                        "target_slug": "mlx-llama-3-3-70b-4bit-instruct",
                        "repo_id": "mlx-community/Llama-3.3-70B-Instruct-4bit",
                        "expected_served_model_identity": "mlx-llama-3-3-70b-4bit-instruct",
                    },
                    "last_known_good_target": {
                        "target_slug": "mlx-llama-3-3-70b-4bit-instruct",
                        "repo_id": "mlx-community/Llama-3.3-70B-Instruct-4bit",
                        "expected_served_model_identity": "mlx-llama-3-3-70b-4bit-instruct",
                    },
                    "actual_served_model_identity": "mlx-llama-3-3-70b-4bit-instruct",
                    "health_state": "serving",
                    "reconciliation_state": "converged",
                    "last_failure": {},
                    "last_transition_time": "2026-03-13T00:00:00Z",
                }
            },
        }
        out = io.StringIO()
        with mock.patch.object(mlxctl, "_registry_path", return_value=Path("/tmp/registry.json")):
            with mock.patch.object(mlxctl, "_load_registry", return_value=data):
                with mock.patch.object(mlxctl, "_port_listening", return_value=[]):
                    with mock.patch.object(mlxctl, "_mlx_pids_for_port", side_effect=lambda port: [123] if port == 8101 else []):
                        with mock.patch.object(mlxctl, "_mlx_runtime_command_for_port", return_value="vllm serve /tmp/model --port 8101"):
                            with mock.patch.object(mlxctl, "_mlx_process_family", return_value="vllm-metal"):
                                with mock.patch.object(mlxctl, "_runtime_model_path_from_command", return_value="/tmp/model"):
                                    with mock.patch.object(mlxctl, "_launchctl_disabled_map", return_value={}):
                                        with mock.patch.object(mlxctl, "_lane_launchd_state", return_value={"label": "com.bebop.mlx-lane.8101", "loaded": True, "disabled": False}):
                                            with mock.patch.object(mlxctl, "_models_endpoint_ok", return_value=True):
                                                with contextlib.redirect_stdout(out):
                                                    mlxctl.cmd_status(argparse.Namespace(checks=True, json=True, table=False))
        payload = json.loads(out.getvalue())
        row = next(item for item in payload["ports"] if item["port"] == 8101)
        self.assertEqual(row["desired_target"]["target_slug"], "mlx-llama-3-3-70b-4bit-instruct")
        self.assertEqual(row["actual_serving_target"]["target_slug"], "mlx-llama-3-3-70b-4bit-instruct")

    def test_status_marks_lane_down_when_target_exists_but_runtime_is_idle(self):
        data = {
            "version": 2,
            "models": {
                "mlx-glm-4-7-flash-4bit-mxfp4": {
                    "model_id": "mlx-glm-4-7-flash-4bit-mxfp4",
                    "cache_path": "/tmp/model",
                    "port": 8102,
                }
            },
            "lanes": {
                "8102": {
                    "port": 8102,
                    "desired_target": {
                        "target_slug": "mlx-glm-4-7-flash-4bit-mxfp4",
                        "repo_id": "mlx-community/GLM-4.7-Flash-4bit-mxfp4",
                        "expected_served_model_identity": "mlx-glm-4-7-flash-4bit-mxfp4",
                    },
                    "actual_serving_target": {
                        "target_slug": "mlx-glm-4-7-flash-4bit-mxfp4",
                        "repo_id": "mlx-community/GLM-4.7-Flash-4bit-mxfp4",
                        "expected_served_model_identity": "mlx-glm-4-7-flash-4bit-mxfp4",
                    },
                    "last_known_good_target": {
                        "target_slug": "mlx-glm-4-7-flash-4bit-mxfp4",
                        "repo_id": "mlx-community/GLM-4.7-Flash-4bit-mxfp4",
                        "expected_served_model_identity": "mlx-glm-4-7-flash-4bit-mxfp4",
                    },
                    "actual_served_model_identity": "mlx-glm-4-7-flash-4bit-mxfp4",
                    "health_state": "serving",
                    "reconciliation_state": "converged",
                    "last_failure": {},
                    "last_transition_time": "2026-03-13T00:00:00Z",
                }
            },
        }
        out = io.StringIO()
        with mock.patch.object(mlxctl, "_registry_path", return_value=Path("/tmp/registry.json")):
            with mock.patch.object(mlxctl, "_load_registry", return_value=data):
                with mock.patch.object(mlxctl, "_port_listening", return_value=[]):
                    with mock.patch.object(mlxctl, "_mlx_pids_for_port", return_value=[]):
                        with mock.patch.object(mlxctl, "_mlx_runtime_command_for_port", return_value=None):
                            with mock.patch.object(mlxctl, "_launchctl_disabled_map", return_value={}):
                                with mock.patch.object(mlxctl, "_lane_launchd_state", return_value={"label": "com.bebop.mlx-lane.8102", "loaded": True, "disabled": False}):
                                    with mock.patch.object(mlxctl, "_models_endpoint_ok", return_value=False):
                                        with contextlib.redirect_stdout(out):
                                            mlxctl.cmd_status(argparse.Namespace(checks=True, json=True, table=False))
        payload = json.loads(out.getvalue())
        row = next(item for item in payload["ports"] if item["port"] == 8102)
        self.assertEqual(row["health_state"], "down")
        self.assertEqual(row["reconciliation_state"], "failed")


if __name__ == "__main__":
    unittest.main()
