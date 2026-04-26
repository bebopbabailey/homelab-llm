from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTER_CONFIG = REPO_ROOT / "services/litellm-orch/config/router.yaml"


class TestRouterDropParams(unittest.TestCase):
    def test_drop_params_enabled(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        litellm_settings = config.get("litellm_settings", {})
        self.assertTrue(
            litellm_settings.get("drop_params"),
            "litellm_settings.drop_params must remain true",
        )

    def test_fast_falls_back_to_deep(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        router_settings = config.get("router_settings", {})
        fallbacks = router_settings.get("fallbacks", [])
        self.assertIn(
            {"fast": ["deep"]},
            fallbacks,
            "router_settings.fallbacks must preserve fast -> deep",
        )

    def test_transcribe_aliases_use_fast_and_deep_lanes(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        aliases = {
            item.get("model_name"): item.get("litellm_params", {})
            for item in config.get("model_list", [])
            if isinstance(item, dict)
        }
        self.assertEqual(
            aliases["task-transcribe"].get("model"),
            "os.environ/LLMSTER_FAST_MODEL",
        )
        self.assertEqual(
            aliases["task-transcribe"].get("api_base"),
            "os.environ/LLMSTER_FAST_API_BASE",
        )
        self.assertEqual(
            aliases["task-transcribe-vivid"].get("model"),
            "os.environ/LLMSTER_DEEP_MODEL",
        )
        self.assertEqual(
            aliases["task-transcribe-vivid"].get("api_base"),
            "os.environ/LLMSTER_DEEP_API_BASE",
        )

    def test_operator_only_chatgpt_alias_exists(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        model_names = {
            item.get("model_name")
            for item in config.get("model_list", [])
            if isinstance(item, dict)
        }
        self.assertIn("chatgpt-5", model_names)
        self.assertNotIn("chatgpt-5-thinking", model_names)

    def test_gpt_request_defaults_excludes_chatgpt_alias(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        guardrails = config.get("guardrails", [])
        targets = None
        for item in guardrails:
            if item.get("guardrail_name") == "gpt-request-defaults":
                targets = item.get("litellm_params", {}).get("target_models", "")
                break
        self.assertIsNotNone(targets, "gpt-request-defaults guardrail must exist")
        target_set = {part.strip() for part in targets.split(",") if part.strip()}
        self.assertNotIn("chatgpt-5", target_set)
        self.assertNotIn("chatgpt-5-thinking", target_set)

    def test_llmster_toolcall_guardrails_target_local_llmster_aliases(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        guardrails = config.get("guardrails", [])
        names = {}
        for item in guardrails:
            name = item.get("guardrail_name")
            if name in {"llmster-toolcall-pre", "llmster-toolcall-post"}:
                names[name] = item.get("litellm_params", {})
        self.assertEqual(
            set(names),
            {"llmster-toolcall-pre", "llmster-toolcall-post"},
            "router must wire both llmster toolcall guardrails",
        )
        for params in names.values():
            self.assertEqual(
                params.get("target_models"),
                "deep,fast,code-reasoning",
            )


if __name__ == "__main__":
    unittest.main()
