from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTER_CONFIG = REPO_ROOT / "services/litellm-orch/config/router.yaml"


class TestChatgptAliasContract(unittest.TestCase):
    def test_chatgpt_alias_points_to_adapter(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        model_list = config.get("model_list", [])
        item = next(x for x in model_list if x.get("model_name") == "chatgpt-5")
        params = item["litellm_params"]
        self.assertEqual(params["model"], "openai/gpt-5.3-codex")
        self.assertEqual(params["api_base"], "os.environ/CCPROXY_ADAPTER_API_BASE")
        self.assertEqual(params["api_key"], "dummy")


if __name__ == "__main__":
    unittest.main()
