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

    def test_fast_falls_back_to_main(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        router_settings = config.get("router_settings", {})
        fallbacks = router_settings.get("fallbacks", [])
        self.assertIn(
            {"fast": ["main"]},
            fallbacks,
            "router_settings.fallbacks must preserve fast -> main",
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


if __name__ == "__main__":
    unittest.main()
