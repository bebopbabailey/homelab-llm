from pathlib import Path
import importlib
import sys
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTER_CONFIG = REPO_ROOT / "services/litellm-orch/config/router.yaml"
CONFIG_DIR = REPO_ROOT / "services/litellm-orch/config"


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

    def test_transcribe_alias_uses_single_public_fast_lane(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        aliases = {
            item.get("model_name"): item.get("litellm_params", {})
            for item in config.get("model_list", [])
            if isinstance(item, dict)
        }
        self.assertIn("task-transcribe", aliases)
        self.assertNotIn("task-transcribe-vivid", aliases)
        self.assertEqual(
            aliases["task-transcribe"].get("model"),
            "os.environ/LLMSTER_FAST_MODEL",
        )
        self.assertEqual(
            aliases["task-transcribe"].get("api_base"),
            "os.environ/LLMSTER_FAST_API_BASE",
        )
        self.assertEqual(aliases["task-transcribe"].get("max_tokens"), 8192)

    def test_transcribe_prompt_uses_native_dotprompt_config(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        prompts = {
            item.get("prompt_id"): item.get("litellm_params", {})
            for item in config.get("prompts", [])
            if isinstance(item, dict)
        }
        guardrail_names = {
            item.get("guardrail_name")
            for item in config.get("guardrails", [])
            if isinstance(item, dict)
        }
        self.assertIn("task-transcribe", prompts)
        self.assertNotIn("task-transcribe-vivid", prompts)
        self.assertEqual(prompts["task-transcribe"].get("prompt_integration"), "dotprompt")
        self.assertEqual(
            prompts["task-transcribe"].get("prompt_file"),
            "./prompts/task-transcribe.prompt",
        )
        self.assertEqual(
            config.get("litellm_settings", {}).get("global_prompt_directory"),
            "./prompts",
        )
        self.assertNotIn("prompt-pre", guardrail_names)

    def test_voice_stt_aliases_use_orin_voice_gateway(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        aliases = {
            item.get("model_name"): item
            for item in config.get("model_list", [])
            if isinstance(item, dict)
        }
        for alias in ("voice-stt-canary", "voice-stt"):
            self.assertIn(alias, aliases)
            params = aliases[alias].get("litellm_params", {})
            self.assertEqual(params.get("model"), "openai/whisper-1")
            self.assertEqual(params.get("api_base"), "os.environ/VOICE_GATEWAY_API_BASE")
            self.assertEqual(params.get("api_key"), "os.environ/VOICE_GATEWAY_API_KEY")
            self.assertEqual(aliases[alias].get("model_info", {}).get("mode"), "audio_transcription")

    def test_youtube_transcript_alias_uses_local_openai_backend(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        aliases = {
            item.get("model_name"): item
            for item in config.get("model_list", [])
            if isinstance(item, dict)
        }
        self.assertIn("task-youtube-transcript", aliases)
        self.assertNotIn("task-youtube-summary", aliases)
        params = aliases["task-youtube-transcript"].get("litellm_params", {})
        self.assertEqual(params.get("model"), "openai/youtube-transcript")
        self.assertEqual(params.get("api_base"), "os.environ/YOUTUBE_TRANSCRIPT_API_BASE")
        self.assertEqual(params.get("api_key"), "dummy")
        self.assertEqual(aliases["task-youtube-transcript"].get("model_info", {}).get("mode"), "chat")

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

    def test_public_responses_contract_guardrails_target_task_aliases_only(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        guardrails = config.get("guardrails", [])
        names = {}
        for item in guardrails:
            name = item.get("guardrail_name")
            if name in {"responses-contract-public-pre", "responses-contract-public-post"}:
                names[name] = item.get("litellm_params", {})
        self.assertEqual(
            set(names),
            {"responses-contract-public-pre", "responses-contract-public-post"},
        )
        for params in names.values():
            self.assertEqual(params.get("target_models"), "deep,fast,task-transcribe,task-json")
            self.assertEqual(params.get("responses_only"), False)

    def test_legacy_transcribe_guardrail_is_not_wired(self):
        config = yaml.safe_load(ROUTER_CONFIG.read_text())
        guardrail_names = {
            item.get("guardrail_name")
            for item in config.get("guardrails", [])
            if isinstance(item, dict)
        }
        self.assertNotIn("transcribe-pre", guardrail_names)
        self.assertNotIn("transcribe-post", guardrail_names)

    def test_router_guardrail_modules_are_importable(self):
        sys.path.insert(0, str(CONFIG_DIR))
        try:
            config = yaml.safe_load(ROUTER_CONFIG.read_text())
            for item in config.get("guardrails", []):
                dotted = item.get("litellm_params", {}).get("guardrail", "")
                module_name, class_name = dotted.rsplit(".", 1)
                module = importlib.import_module(module_name)
                self.assertTrue(hasattr(module, class_name), dotted)
        finally:
            try:
                sys.path.remove(str(CONFIG_DIR))
            except ValueError:
                pass


if __name__ == "__main__":
    unittest.main()
