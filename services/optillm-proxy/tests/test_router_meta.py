import unittest
import importlib.util
import pathlib

try:
    from optillm.plugins import router_meta_plugin  # type: ignore
except ImportError:
    plugin_path = pathlib.Path(__file__).resolve().parents[1] / "optillm" / "plugins" / "router_meta_plugin.py"
    spec = importlib.util.spec_from_file_location("router_meta_plugin", plugin_path)
    assert spec and spec.loader
    router_meta_plugin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(router_meta_plugin)


class RouterMetaPayloadTests(unittest.TestCase):
    def test_build_forward_payload_strips_optillm_approach(self):
        raw = {"model": "mlx-test", "messages": [{"role": "user", "content": "hi"}], "optillm_approach": "router_meta"}
        payload = router_meta_plugin._build_forward_payload(raw, "bon-mlx-test")
        self.assertEqual(payload["model"], "bon-mlx-test")
        self.assertNotIn("optillm_approach", payload)

    def test_auth_header_prefers_override(self):
        header = router_meta_plugin._auth_header("localkey", "Bearer other")
        self.assertEqual(header["Authorization"], "Bearer localkey")

    def test_choose_destination_defaults(self):
        router_meta_plugin.LOCAL_ONLY = {"bon"}
        router_meta_plugin.PROXY_ONLY = set()
        router_meta_plugin.DEFAULT_DESTINATION = "proxy"
        self.assertEqual(router_meta_plugin._choose_destination("bon"), "local")
        self.assertEqual(router_meta_plugin._choose_destination("z3"), "proxy")

    def test_parse_set(self):
        self.assertEqual(router_meta_plugin._parse_set("", {"a"}), {"a"})
        self.assertEqual(router_meta_plugin._parse_set("bon, moa", set()), {"bon", "moa"})


if __name__ == "__main__":
    unittest.main()
