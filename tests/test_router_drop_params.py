from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTER_CONFIG = REPO_ROOT / "layer-gateway/litellm-orch/config/router.yaml"


class TestRouterDropParams(unittest.TestCase):
    def test_drop_params_enabled(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        litellm_settings = config.get("litellm_settings", {})
        self.assertTrue(
            litellm_settings.get("drop_params"),
            "litellm_settings.drop_params must remain true",
        )


if __name__ == "__main__":
    unittest.main()
