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

    def test_fast_falls_back_to_main(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        router_settings = config.get("router_settings", {})
        fallbacks = router_settings.get("fallbacks", [])
        self.assertIn(
            {"fast": ["main"]},
            fallbacks,
            "router_settings.fallbacks must preserve fast -> main",
        )


if __name__ == "__main__":
    unittest.main()
