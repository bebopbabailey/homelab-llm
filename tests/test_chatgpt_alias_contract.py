from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTER_CONFIG = REPO_ROOT / "layer-gateway/litellm-orch/config/router.yaml"


def _alias(name: str):
    config = yaml.safe_load(ROUTER_CONFIG.read_text())
    for entry in config["model_list"]:
        if entry["model_name"] == name:
            return entry
    raise AssertionError(f"missing alias {name}")


class TestChatgptAliasContract(unittest.TestCase):
    def test_chatgpt_5_contract(self):
        alias = _alias("chatgpt-5")
        self.assertEqual(alias["litellm_params"]["model"], "chatgpt/gpt-5.4")
        self.assertEqual(alias["model_info"]["mode"], "responses")
        self.assertNotIn("api_base", alias["litellm_params"])
        self.assertNotIn("api_key", alias["litellm_params"])
        self.assertNotIn("max_tokens", alias["litellm_params"])

    def test_chatgpt_5_thinking_contract(self):
        alias = _alias("chatgpt-5-thinking")
        self.assertEqual(alias["litellm_params"]["model"], "chatgpt/gpt-5.4-pro")
        self.assertEqual(alias["model_info"]["mode"], "responses")
        self.assertNotIn("api_base", alias["litellm_params"])
        self.assertNotIn("api_key", alias["litellm_params"])
        self.assertNotIn("max_tokens", alias["litellm_params"])


if __name__ == "__main__":
    unittest.main()
