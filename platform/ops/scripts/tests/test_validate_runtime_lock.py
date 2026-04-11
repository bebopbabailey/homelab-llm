import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import importlib.util

SPEC = importlib.util.spec_from_file_location(
    "validate_runtime_lock",
    str(Path(__file__).resolve().parents[1] / "validate_runtime_lock.py"),
)
vr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vr)


class ValidateRuntimeLockTests(unittest.TestCase):
    def test_router_assertions(self):
        text = 'litellm_settings:\n  drop_params: true\nrouter_settings:\n  fallbacks:\n    - {"fast": ["main"]}\n'
        self.assertEqual(vr.router_assertions(text), (True, True))

    def test_fast_fails_when_patch_artifact_present(self):
        lock = {"service_refs": {"litellm-orch": {"path": "layer-gateway/litellm-orch"}}, "submodules": {"layer-gateway/optillm-proxy": "abc", "layer-gateway/litellm-orch": "def"}, "litellm": {"router_config_ref": {"service_id": "litellm-orch", "relpath": "config/router.yaml"}}}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "layer-gateway/optillm-proxy/scripts").mkdir(parents=True)
            (root / "layer-gateway/optillm-proxy/patches").mkdir(parents=True)
            (root / "layer-gateway/optillm-proxy/pyproject.toml").write_text('optillm==0.3.12')
            (root / "layer-gateway/optillm-proxy/uv.lock").write_text('source = { registry = "https://pypi.org/simple" }')
            (root / "layer-gateway/optillm-proxy/scripts/deploy_studio.sh").write_text('git checkout --detach\nuv sync --frozen\n')
            (root / "layer-gateway/litellm-orch/config").mkdir(parents=True)
            (root / "layer-gateway/litellm-orch/config/router.yaml").write_text('drop_params: true\nfallbacks:\n  - {"fast": ["main"]}\n')
            for doc in [
                'docs/foundation/runtime-lock.md','docs/_core/SOURCES_OF_TRUTH.md','docs/_core/CHANGE_RULES.md','docs/foundation/testing.md',
                'layer-gateway/optillm-proxy/SERVICE_SPEC.md','layer-gateway/optillm-proxy/RUNBOOK.md','layer-gateway/optillm-proxy/AGENTS.md',
                'layer-gateway/litellm-orch/SERVICE_SPEC.md','layer-gateway/litellm-orch/RUNBOOK.md','docs/foundation/mlx-registry.md','docs/PLATFORM_DOSSIER.md','docs/INTEGRATIONS.md']:
                p = root / doc
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('x')
            (root / "layer-gateway/optillm-proxy/patches/optillm.patch").write_text('patch')
            with mock.patch.object(vr, "REPO_ROOT", root), \
                 mock.patch.object(vr, "PATCH_PATHS", [root / "layer-gateway/optillm-proxy/patches/optillm.patch"]), \
                 mock.patch.object(vr, "DOC_PATHS", [root / 'docs/foundation/runtime-lock.md']), \
                 mock.patch.object(vr, "gitlink_sha", side_effect=lambda path: lock['submodules'][path]):
                failures = vr.check_fast(lock)
            self.assertTrue(any("patch artifact present" in f for f in failures))

    def test_fast_fails_when_router_missing_drop_params(self):
        lock = {"submodules": {"layer-gateway/optillm-proxy": "abc", "layer-gateway/litellm-orch": "def"}, "litellm": {"router_yaml": "router.yaml"}}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "router.yaml").write_text('router_settings:\n  fallbacks:\n    - {"fast": ["main"]}\n')
            (root / "layer-gateway/optillm-proxy").mkdir(parents=True)
            (root / "layer-gateway/optillm-proxy/pyproject.toml").write_text('optillm==0.3.12')
            (root / "layer-gateway/optillm-proxy/uv.lock").write_text('registry')
            (root / "layer-gateway/optillm-proxy/scripts").mkdir(parents=True)
            (root / "layer-gateway/optillm-proxy/scripts/deploy_studio.sh").write_text('git checkout --detach\nuv sync --frozen\n')
            (root / 'doc.md').write_text('x')
            with mock.patch.object(vr, "REPO_ROOT", root), \
                 mock.patch.object(vr, "PATCH_PATHS", []), \
                 mock.patch.object(vr, "DOC_PATHS", [root / 'doc.md']), \
                 mock.patch.object(vr, "gitlink_sha", side_effect=lambda path: lock['submodules'][path]):
                failures = vr.check_fast(lock)
            self.assertTrue(any('drop_params' in f for f in failures))

    def test_fast_fails_when_uv_lock_has_git_source(self):
        lock = {"submodules": {"layer-gateway/optillm-proxy": "abc", "layer-gateway/litellm-orch": "def"}, "litellm": {"router_yaml": "router.yaml"}}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "router.yaml").write_text('drop_params: true\nfallbacks:\n  - {"fast": ["main"]}\n')
            (root / "layer-gateway/optillm-proxy/scripts").mkdir(parents=True)
            (root / "layer-gateway/optillm-proxy/pyproject.toml").write_text('optillm==0.3.12')
            (root / "layer-gateway/optillm-proxy/uv.lock").write_text('git+https://github.com/algorithmicsuperintelligence/optillm')
            (root / "layer-gateway/optillm-proxy/scripts/deploy_studio.sh").write_text('git checkout --detach\nuv sync --frozen\n')
            (root / 'doc.md').write_text('x')
            with mock.patch.object(vr, "REPO_ROOT", root), \
                 mock.patch.object(vr, "PATCH_PATHS", []), \
                 mock.patch.object(vr, "DOC_PATHS", [root / 'doc.md']), \
                 mock.patch.object(vr, "gitlink_sha", side_effect=lambda path: lock['submodules'][path]):
                failures = vr.check_fast(lock)
            self.assertTrue(any('git-sourced optillm' in f for f in failures))

    def test_parse_remote_json(self):
        proc = mock.Mock(returncode=0, stdout=json.dumps({"ok": True}), stderr='')
        self.assertEqual(vr.parse_remote_json(proc, 'ctx'), {"ok": True})

    def test_parse_remote_json_raises(self):
        proc = mock.Mock(returncode=1, stdout='', stderr='bad')
        with self.assertRaises(RuntimeError):
            vr.parse_remote_json(proc, 'ctx')

    def test_lane_override_assertions(self):
        argv = [
            "vllm",
            "serve",
            "--enable-auto-tool-choice",
            "--tool-call-parser",
            "hermes",
        ]
        override = {
            "tool_choice_mode": "auto",
            "tool_call_parser": "hermes",
            "reasoning_parser": None,
        }
        self.assertEqual(vr.lane_override_assertions(argv, override), [])

    def test_lane_override_assertions_flags_unexpected_reasoning_parser(self):
        argv = [
            "vllm",
            "serve",
            "--enable-auto-tool-choice",
            "--tool-call-parser",
            "hermes",
            "--reasoning-parser",
            "qwen3",
        ]
        override = {
            "tool_choice_mode": "auto",
            "tool_call_parser": "hermes",
            "reasoning_parser": None,
        }
        failures = vr.lane_override_assertions(argv, override)
        self.assertTrue(any("unexpected --reasoning-parser" in failure for failure in failures))

    def test_parse_systemd_execstart(self):
        text = "ExecStart=/path/to/litellm --config x --host 0.0.0.0 --port 4000\n"
        self.assertEqual(vr.parse_systemd_execstart(text), ("0.0.0.0", 4000))


if __name__ == '__main__':
    unittest.main()
