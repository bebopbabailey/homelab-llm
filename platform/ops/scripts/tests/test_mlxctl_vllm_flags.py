import importlib.machinery
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "mlxctl"
LOADER = importlib.machinery.SourceFileLoader("mlxctl_module", str(MODULE_PATH))
SPEC = importlib.util.spec_from_loader("mlxctl_module", LOADER)
mlxctl = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mlxctl)


class MlxctlVllmFlagsTests(unittest.TestCase):
    def test_default_profile_main_lane(self):
        entry = {"model_id": "mlx-qwen3-next-80b-mxfp4-a3b-instruct"}
        self.assertEqual(mlxctl._default_vllm_profile(entry), "qwen3_main")
        self.assertEqual(mlxctl._default_vllm_tool_choice_mode(entry), "auto")
        self.assertEqual(mlxctl._default_vllm_tool_parser(entry), "qwen3")

    def test_default_memory_fraction_is_auto(self):
        entry = {
            "model_id": "mlx-gpt-oss-20b-mxfp4-q4",
            "vllm_max_model_len": 32768,
            "vllm_async_scheduling": False,
        }
        self.assertEqual(mlxctl._default_vllm_max_model_len(entry), 32768)
        self.assertEqual(mlxctl._default_vllm_memory_fraction(entry), "auto")
        self.assertFalse(mlxctl._default_vllm_async_scheduling(entry))

    def test_numeric_memory_fraction_rejected(self):
        entry = {
            "model_id": "mlx-gpt-oss-20b-mxfp4-q4",
            "vllm_memory_fraction": "0.45",
        }
        with self.assertRaises(SystemExit):
            mlxctl._validated_vllm_memory_fraction(entry)

    def test_parser_alias_resolution_prefers_qwen3_xml(self):
        caps = {"tool_call_parsers": ["qwen3_xml", "qwen3_coder"]}
        self.assertEqual(mlxctl._resolve_tool_call_parser("qwen3", caps), "qwen3_xml")

    def test_compile_requires_auto_tool_capability(self):
        entry = {
            "model_id": "mlx-qwen3-next-80b-mxfp4-a3b-instruct",
            "cache_path": "/tmp/model",
            "vllm": {"tool_choice_mode": "auto", "tool_call_parser": "qwen3"},
        }
        caps = {
            "vllm_bin": "/usr/bin/vllm",
            "supports_auto_tool_choice": False,
            "supports_tool_call_parser": True,
            "supports_reasoning_parser": True,
            "tool_call_parsers": ["qwen3_xml"],
        }
        with self.assertRaises(SystemExit):
            mlxctl._compile_vllm_launch(entry, 8101, "0.0.0.0", caps, validate=True)

    def test_compile_auto_tool_success(self):
        entry = {
            "model_id": "mlx-qwen3-next-80b-mxfp4-a3b-instruct",
            "cache_path": "/tmp/model",
            "vllm": {"tool_choice_mode": "auto", "tool_call_parser": "qwen3", "reasoning_parser": "qwen3"},
        }
        caps = {
            "vllm_bin": "/usr/bin/vllm",
            "supports_auto_tool_choice": True,
            "supports_tool_call_parser": True,
            "supports_reasoning_parser": True,
            "tool_call_parsers": ["qwen3_xml"],
        }
        with mock.patch.dict(os.environ, {"MLX_MLX_QWEN3_NEXT_80B_MXFP4_A3B_INSTRUCT_API_KEY": "test-key"}, clear=False):
            compiled = mlxctl._compile_vllm_launch(entry, 8101, "0.0.0.0", caps, validate=True)
        argv = " ".join(compiled["argv"])
        self.assertIn("--enable-auto-tool-choice", argv)
        self.assertIn("--tool-call-parser qwen3_xml", argv)
        self.assertIn("--reasoning-parser qwen3", argv)
        self.assertIn("--api-key test-key", argv)
        self.assertIn("--no-async-scheduling", argv)
        self.assertEqual(compiled["env"]["VLLM_METAL_MEMORY_FRACTION"], "auto")

    def test_update_env_local_preserves_existing_real_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "env.local"
            path.write_text("KEEP=1\nMLX_MLX_GPT_OSS_20B_MXFP4_Q4_API_KEY=real-key\n")
            mlxctl._update_env_local(
                path,
                [{"handle": "mlx-gpt-oss-20b-mxfp4-q4", "endpoint_port": 8102}],
                "192.168.1.72",
            )
            text = path.read_text()
            self.assertIn("KEEP=1", text)
            self.assertIn("MLX_MLX_GPT_OSS_20B_MXFP4_Q4_API_KEY=real-key", text)

    def test_update_env_local_missing_key_renders_blank(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "env.local"
            path.write_text("KEEP=1\n")
            mlxctl._update_env_local(
                path,
                [{"handle": "mlx-gpt-oss-20b-mxfp4-q4", "endpoint_port": 8102}],
                "192.168.1.72",
            )
            text = path.read_text()
            self.assertIn("MLX_MLX_GPT_OSS_20B_MXFP4_Q4_API_KEY=\n", text)
            self.assertNotIn("MLX_MLX_GPT_OSS_20B_MXFP4_Q4_API_KEY=dummy", text)

    def test_parse_launchctl_print_disabled(self):
        sample = """
disabled services = {
  "com.bebop.mlx-lane.8100" => true
  "com.bebop.mlx-lane.8101" => false
}
"""
        parsed = mlxctl._parse_launchctl_print_disabled(sample)
        self.assertEqual(parsed.get("com.bebop.mlx-lane.8100"), True)
        self.assertEqual(parsed.get("com.bebop.mlx-lane.8101"), False)

    def test_repair_lanes_is_mutating_only_with_apply(self):
        dry = type("Args", (), {"command": "repair-lanes", "apply": False})()
        do_apply = type("Args", (), {"command": "repair-lanes", "apply": True})()
        self.assertFalse(mlxctl._is_mutating_command(dry))
        self.assertTrue(mlxctl._is_mutating_command(do_apply))

    def test_parse_port_csv_validates_and_deduplicates(self):
        ports = mlxctl._parse_port_csv("8101,8100,8101", arg_name="--ports", valid_range=mlxctl.TEAM_RANGE)
        self.assertEqual(ports, [8100, 8101])

    def test_parse_port_csv_rejects_invalid(self):
        with self.assertRaises(SystemExit):
            mlxctl._parse_port_csv("abc", arg_name="--ports", valid_range=mlxctl.TEAM_RANGE)
        with self.assertRaises(SystemExit):
            mlxctl._parse_port_csv("9000", arg_name="--ports", valid_range=mlxctl.TEAM_RANGE)

    def test_detect_vllm_capabilities_rejects_unusable_help(self):
        fake_result = mock.Mock(returncode=0, stdout="usage: something else", stderr="")
        with mock.patch.object(mlxctl.Path, "exists", return_value=True):
            with mock.patch.object(mlxctl.subprocess, "run", return_value=fake_result):
                with self.assertRaises(SystemExit):
                    mlxctl._detect_vllm_capabilities(vllm_bin="/usr/bin/vllm")


if __name__ == "__main__":
    unittest.main()
