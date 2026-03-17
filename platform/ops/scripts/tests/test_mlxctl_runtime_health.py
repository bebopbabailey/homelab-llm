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

    def test_vllm_render_validate_reports_auto_memory_fraction_without_lane_auth(self):
        data = {
            "models": {
                "mlx-gpt-oss-120b-mxfp4-q4": {
                    "model_id": "mlx-gpt-oss-120b-mxfp4-q4",
                    "cache_path": __file__,
                    "port": 8100,
                }
            }
        }
        caps = {
            "vllm_bin": "/usr/bin/vllm",
            "supports_auto_tool_choice": True,
            "supports_tool_call_parser": True,
            "supports_reasoning_parser": True,
            "supports_default_chat_template_kwargs": True,
            "tool_call_parsers": ["qwen3_xml"],
        }
        self._patch("_registry_path", lambda: Path("/tmp/registry.json"))
        self._patch("_load_registry", lambda _path: data)
        self._patch("_detect_vllm_capabilities", lambda: caps)
        payload = mlxctl._render_vllm_rows_for_ports([8100], host="127.0.0.1", validate=True)
        self.assertEqual(len(payload["rows"]), 1)
        row = payload["rows"][0]
        self.assertEqual(row["env"]["VLLM_METAL_MEMORY_FRACTION"], "auto")
        self.assertNotIn("--api-key", row["argv"])
        self.assertIn("--no-async-scheduling", row["argv"])
        self.assertIn("--default-chat-template-kwargs", row["argv"])

    def test_chat_probe_payload_uses_supplied_max_tokens(self):
        payload = mlxctl._chat_probe_payload("mlx-seed-oss-36b-4bit-instruct", "chat_tool_noop", max_tokens=128)
        self.assertEqual(payload["max_tokens"], 128)
        self.assertEqual(payload["tool_choice"], "auto")

    def test_chat_probe_accepts_noop_tool_name_only_when_requested(self):
        good = {"tool_calls": [{"function": {"name": "noop"}}]}
        bad = {"tool_calls": [{"function": {"name": "example_function_name"}}]}
        self.assertTrue(mlxctl._chat_probe_accepts(good, "noop_tool_call", "chat_tool_noop"))
        self.assertFalse(mlxctl._chat_probe_accepts(bad, "noop_tool_call", "chat_tool_noop"))

    def test_vllm_render_generic_hermes_override_skips_reasoning_parser(self):
        data = {
            "models": {
                "mlx-qwen3-next-80b-mxfp4-a3b-instruct": {
                    "model_id": "mlx-qwen3-next-80b-mxfp4-a3b-instruct",
                    "cache_path": __file__,
                    "port": 8101,
                    "tool_call_parser": "qwen3",
                    "reasoning_parser": "qwen3",
                    "vllm": {
                        "profile": "generic",
                        "tool_choice_mode": "auto",
                        "tool_call_parser": "hermes",
                        "reasoning_parser": None,
                    },
                }
            }
        }
        caps = {
            "vllm_bin": "/usr/bin/vllm",
            "supports_auto_tool_choice": True,
            "supports_tool_call_parser": True,
            "supports_reasoning_parser": True,
            "supports_default_chat_template_kwargs": True,
            "tool_call_parsers": ["hermes", "qwen3_xml"],
        }
        self._patch("_registry_path", lambda: Path("/tmp/registry.json"))
        self._patch("_load_registry", lambda _path: data)
        self._patch("_detect_vllm_capabilities", lambda: caps)
        payload = mlxctl._render_vllm_rows_for_ports([8101], host="127.0.0.1", validate=True)
        row = payload["rows"][0]
        self.assertIn("--enable-auto-tool-choice", row["argv"])
        self.assertIn("hermes", row["argv"])
        self.assertNotIn("--reasoning-parser", row["argv"])

    def test_seed_profile_adds_trust_remote_code_and_local_chat_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = Path(tmpdir)
            (model_dir / "chat_template.jinja").write_text("{{ messages }}")
            entry = {
                "model_id": "mlx-seed-oss-36b-4bit-instruct",
                "cache_path": str(model_dir),
                "repo_id": "mlx-community/Seed-OSS-36B-Instruct-4bit",
                "vllm": {"profile": "seed_oss", "tool_choice_mode": "auto"},
            }
            caps = {
                "vllm_bin": "/usr/bin/vllm",
                "supports_auto_tool_choice": True,
                "supports_tool_call_parser": True,
                "supports_reasoning_parser": True,
                "supports_default_chat_template_kwargs": True,
                "tool_call_parsers": ["seed_oss"],
                "reasoning_parsers": [],
            }
            compiled = mlxctl._compile_vllm_launch(entry, 8102, "127.0.0.1", caps, validate=True)
            self.assertIn("--trust-remote-code", compiled["argv"])
            self.assertIn("--chat-template", compiled["argv"])
            self.assertIn(str(model_dir / "chat_template.jinja"), compiled["argv"])

    def test_restart_team_lane_allows_partial(self):
        captured = {}

        def fake_start(args):
            captured["ports"] = args.ports
            captured["allow_partial"] = getattr(args, "allow_partial", None)

        self._patch("cmd_mlx_launch_start", fake_start)

        mlxctl._restart_team_lane(8101)

        self.assertEqual(captured["ports"], "8101")
        self.assertTrue(captured["allow_partial"])

    def test_cmd_load_force_reloads_registry_after_unload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = Path(tmpdir) / "registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "models": {
                            "old-model": {
                                "model_id": "old-model",
                                "repo_id": "org/old-model",
                                "cache_path": "/tmp/old",
                                "port": 8101,
                            },
                            "new-model": {
                                "model_id": "new-model",
                                "repo_id": "org/new-model",
                                "cache_path": "/tmp/new",
                                "port": None,
                            },
                        },
                    }
                )
            )

            def fake_unload(args):
                payload = json.loads(registry.read_text())
                for entry in payload["models"].values():
                    if entry.get("port") == 8101:
                        entry["port"] = None
                registry.write_text(json.dumps(payload))

            self._patch("_registry_path", lambda: registry)
            self._patch("_launchd_loaded", lambda _label: False)
            self._patch("_mlx_pids_for_port", lambda _port: [1234])
            self._patch("_port_listening", lambda _port: [])
            self._patch("_detect_vllm_capabilities", lambda: {
                "vllm_bin": "/usr/bin/vllm",
                "supports_auto_tool_choice": True,
                "supports_tool_call_parser": True,
                "supports_reasoning_parser": True,
                "supports_default_chat_template_kwargs": True,
                "tool_call_parsers": ["llama3_json", "qwen3_xml", "glm47"],
                "reasoning_parsers": ["glm45", "qwen3"],
            })
            self._patch("_preflight_architecture", lambda _entry, _caps: {"config_ok": True})
            self._patch("_preflight_family_runtime", lambda _entry, _caps: {"profile_name": "generic"})
            self._patch("_wait_for_vllm_readiness", lambda _port, _entry, _compiled, timeout=0: {"ok": True, "served_model_identity": "new-model"})
            self._patch("_restart_team_lane", lambda _port: None)
            self._patch("_raw_harmony_tags_detected", lambda _port, _model: False)
            self._patch("_raw_qwen3_tags_detected", lambda _port, _model: False)

            mlxctl.cmd_load(
                argparse.Namespace(
                    model="org/new-model",
                    port="8101",
                    force=True,
                    ignore_launchd=False,
                    convert="auto",
                    name=None,
                    offload_og=False,
                    preconverted="auto",
                    sync=False,
                )
            )

            payload = json.loads(registry.read_text())
            self.assertIsNone(payload["models"]["old-model"]["port"])
            self.assertEqual(payload["models"]["new-model"]["port"], 8101)
            assigned_8101 = sorted(
                slug for slug, entry in payload["models"].items() if entry.get("port") == 8101
            )
            self.assertEqual(assigned_8101, ["new-model"])
            lane = payload["lanes"]["8101"]
            self.assertEqual(lane["desired_target"]["target_slug"], "new-model")
            self.assertEqual(lane["actual_serving_target"]["target_slug"], "new-model")

    def test_cmd_load_force_unloads_assigned_idle_port(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = Path(tmpdir) / "registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "models": {
                            "old-model": {
                                "model_id": "old-model",
                                "repo_id": "org/old-model",
                                "cache_path": "/tmp/old",
                                "port": 8102,
                            },
                            "new-model": {
                                "model_id": "new-model",
                                "repo_id": "org/new-model",
                                "cache_path": "/tmp/new",
                                "port": None,
                            },
                        },
                    }
                )
            )

            unload_calls = []

            def fake_unload(args):
                unload_calls.append(args.port)
                payload = json.loads(registry.read_text())
                for entry in payload["models"].values():
                    if entry.get("port") == 8102:
                        entry["port"] = None
                registry.write_text(json.dumps(payload))

            self._patch("_registry_path", lambda: registry)
            self._patch("_launchd_loaded", lambda _label: False)
            self._patch("_mlx_pids_for_port", lambda _port: [])
            self._patch("_port_listening", lambda _port: [])
            self._patch("_detect_vllm_capabilities", lambda: {
                "vllm_bin": "/usr/bin/vllm",
                "supports_auto_tool_choice": True,
                "supports_tool_call_parser": True,
                "supports_reasoning_parser": True,
                "supports_default_chat_template_kwargs": True,
                "tool_call_parsers": ["llama3_json", "qwen3_xml", "glm47"],
                "reasoning_parsers": ["glm45", "qwen3"],
            })
            self._patch("_preflight_architecture", lambda _entry, _caps: {"config_ok": True})
            self._patch("_preflight_family_runtime", lambda _entry, _caps: {"profile_name": "generic"})
            self._patch("_wait_for_vllm_readiness", lambda _port, _entry, _compiled, timeout=0: {"ok": True, "served_model_identity": "new-model"})
            self._patch("_restart_team_lane", lambda _port: None)
            self._patch("_raw_harmony_tags_detected", lambda _port, _model: False)
            self._patch("_raw_qwen3_tags_detected", lambda _port, _model: False)

            mlxctl.cmd_load(
                argparse.Namespace(
                    model="org/new-model",
                    port="8102",
                    force=True,
                    ignore_launchd=False,
                    convert="auto",
                    name=None,
                    offload_og=False,
                    preconverted="auto",
                    sync=False,
                )
            )

            payload = json.loads(registry.read_text())
            self.assertIsNone(payload["models"]["old-model"]["port"])
            self.assertEqual(payload["models"]["new-model"]["port"], 8102)
            lane = payload["lanes"]["8102"]
            self.assertEqual(lane["actual_serving_target"]["target_slug"], "new-model")

    def test_cmd_load_preflight_failure_preserves_actual_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = Path(tmpdir) / "registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "models": {
                            "old-model": {
                                "model_id": "old-model",
                                "repo_id": "org/old-model",
                                "cache_path": "/tmp/old",
                                "port": 8101
                            },
                            "new-model": {
                                "model_id": "new-model",
                                "repo_id": "org/new-model",
                                "cache_path": "/tmp/new",
                                "port": None
                            }
                        },
                        "lanes": {
                            "8101": {
                                "port": 8101,
                                "desired_target": {
                                    "target_slug": "old-model",
                                    "repo_id": "org/old-model",
                                    "expected_served_model_identity": "old-model"
                                },
                                "actual_serving_target": {
                                    "target_slug": "old-model",
                                    "repo_id": "org/old-model",
                                    "expected_served_model_identity": "old-model"
                                },
                                "last_known_good_target": {
                                    "target_slug": "old-model",
                                    "repo_id": "org/old-model",
                                    "expected_served_model_identity": "old-model"
                                },
                                "actual_served_model_identity": "old-model",
                                "health_state": "serving",
                                "reconciliation_state": "converged",
                                "last_failure": {},
                                "last_transition_time": None
                            }
                        }
                    }
                )
            )

            self._patch("_registry_path", lambda: registry)
            self._patch("_launchd_loaded", lambda _label: False)
            self._patch("_mlx_pids_for_port", lambda _port: [111])
            self._patch("_port_listening", lambda _port: [])
            self._patch("_detect_vllm_capabilities", lambda: {
                "vllm_bin": "/usr/bin/vllm",
                "supports_auto_tool_choice": True,
                "supports_tool_call_parser": True,
                "supports_reasoning_parser": True,
                "tool_call_parsers": ["llama3_json", "glm47"],
                "reasoning_parsers": ["glm45"],
            })
            self._patch("_preflight_architecture", mock.Mock(side_effect=SystemExit("unsupported architecture")))

            with self.assertRaises(SystemExit):
                mlxctl.cmd_load(
                    argparse.Namespace(
                        model="org/new-model",
                        port="8101",
                        force=True,
                        ignore_launchd=False,
                        convert="auto",
                        name=None,
                        offload_og=False,
                        preconverted="auto",
                        sync=False,
                    )
                )

            payload = json.loads(registry.read_text())
            lane = payload["lanes"]["8101"]
            self.assertEqual(lane["desired_target"]["target_slug"], "new-model")
            self.assertEqual(lane["actual_serving_target"]["target_slug"], "old-model")
            self.assertEqual(payload["models"]["old-model"]["port"], 8101)
            self.assertIsNone(payload["models"]["new-model"]["port"])

    def test_verify_fails_when_serving_lane_has_no_actual_target(self):
        data = {
            "version": 2,
            "models": {
                "mlx-gpt-oss-20b-mxfp4-q4": {
                    "model_id": "mlx-gpt-oss-20b-mxfp4-q4",
                    "repo_id": "mlx-community/gpt-oss-20b-MXFP4-Q4",
                    "cache_path": __file__,
                    "context_length": 32768,
                    "max_output_tokens": 16384,
                    "chat_template": __file__,
                    "tool_call_parser": "harmony",
                    "reasoning_parser": "harmony",
                    "port": 8102,
                }
            },
            "lanes": {
                "8102": {
                    "desired_target": {
                        "target_slug": "mlx-gpt-oss-20b-mxfp4-q4",
                        "repo_id": "mlx-community/gpt-oss-20b-MXFP4-Q4",
                        "expected_served_model_identity": "mlx-gpt-oss-20b-mxfp4-q4",
                    },
                    "actual_serving_target": None,
                    "last_known_good_target": None,
                    "actual_served_model_identity": "mlx-gpt-oss-20b-mxfp4-q4",
                    "health_state": "serving",
                    "reconciliation_state": "failed",
                    "last_failure": {},
                    "last_transition_time": None,
                }
            },
        }
        self._patch("_registry_path", lambda: Path("/tmp/registry.json"))
        self._patch("_load_registry", lambda _path: data)
        self._patch("_launchctl_disabled_map", lambda: {})
        self._patch("_lane_launchd_state", lambda _port, disabled_map=None: {"label": "com.bebop.mlx-lane.8102", "loaded": True, "disabled": False})
        self._patch("_mlx_runtime_command_for_port", lambda _port: f"vllm serve {__file__} --port 8102")
        self._patch("_runtime_model_path_from_command", lambda _cmd: __file__)
        self._patch("_detect_vllm_capabilities", lambda: {
            "vllm_bin": "/usr/bin/vllm",
            "supports_auto_tool_choice": True,
            "supports_tool_call_parser": True,
            "supports_reasoning_parser": False,
            "supports_default_chat_template_kwargs": True,
            "tool_call_parsers": ["openai", "llama3_json"],
            "reasoning_parsers": [],
        })
        self._patch("_models_endpoint_ok", lambda port, timeout=2: port == 8102)
        with self.assertRaises(SystemExit) as exc:
            mlxctl.cmd_verify(argparse.Namespace(fix_defaults=False))
        self.assertIn("actual_serving_target is null", str(exc.exception))


if __name__ == "__main__":
    unittest.main()
