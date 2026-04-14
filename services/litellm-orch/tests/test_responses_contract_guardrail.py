import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "services/litellm-orch/config/responses_contract_guardrail.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


responses_contract_guardrail = _load_module(MODULE_PATH, "responses_contract_guardrail")
ResponsesContractGuardrail = responses_contract_guardrail.ResponsesContractGuardrail


class TestResponsesContractGuardrail(unittest.IsolatedAsyncioTestCase):
    async def test_non_target_model_passthrough(self):
        guardrail = ResponsesContractGuardrail(
            guardrail_name="responses-contract-pre",
            event_hook="pre_call",
            default_on=True,
        )
        data = {"model": "main", "stream": True}
        out = await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="responses",
        )
        self.assertIs(out, data)
        self.assertTrue(out["stream"])

    async def test_normalizes_stream_and_temperature(self):
        guardrail = ResponsesContractGuardrail(
            guardrail_name="responses-contract-pre",
            event_hook="pre_call",
            default_on=True,
            target_models="chatgpt-5",
        )
        data = {
            "model": "chatgpt-5",
            "stream": True,
            "tools": [{"type": "function", "name": "noop"}],
            "tool_choice": "auto",
        }
        captured = []
        with patch.object(responses_contract_guardrail, "emit_policy_event", side_effect=captured.append):
            out = await guardrail.async_pre_call_hook(
                user_api_key_dict=None,
                cache=None,
                data=data,
                call_type="responses",
            )
        self.assertFalse(out["stream"])
        self.assertEqual(out["temperature"], 0.0)
        self.assertEqual(out["tools"], [{"type": "function", "name": "noop"}])
        self.assertEqual(out["tool_choice"], "auto")
        self.assertEqual(captured[0]["decision"], "normalized")
        self.assertEqual(captured[0]["normalized_fields"], ["stream", "temperature"])
        self.assertEqual(captured[1]["event_type"], "policy_summary")

    async def test_passthrough_when_already_constrained(self):
        guardrail = ResponsesContractGuardrail(
            guardrail_name="responses-contract-pre",
            event_hook="pre_call",
            default_on=True,
        )
        data = {
            "model": "chatgpt-5",
            "stream": False,
            "temperature": 0.0,
            "input": "hello",
        }
        captured = []
        with patch.object(responses_contract_guardrail, "emit_policy_event", side_effect=captured.append):
            out = await guardrail.async_pre_call_hook(
                user_api_key_dict=None,
                cache=None,
                data=data,
                call_type="responses",
            )
        self.assertFalse(out["stream"])
        self.assertEqual(out["temperature"], 0.0)
        self.assertEqual(out["input"], "hello")
        self.assertEqual(captured[0]["decision"], "passthrough")

    async def test_rejects_non_responses_call_type(self):
        guardrail = ResponsesContractGuardrail(
            guardrail_name="responses-contract-pre",
            event_hook="pre_call",
            default_on=True,
        )
        data = {"model": "chatgpt-5", "messages": [{"role": "user", "content": "hi"}]}
        captured = []
        with patch.object(responses_contract_guardrail, "emit_policy_event", side_effect=captured.append):
            with self.assertRaises(Exception) as ctx:
                await guardrail.async_pre_call_hook(
                    user_api_key_dict=None,
                    cache=None,
                    data=data,
                    call_type="completion",
                )
        self.assertIn("model chatgpt-5 only accepts /v1/responses requests", str(ctx.exception))
        self.assertEqual(captured[0]["decision"], "rejected")

    async def test_post_call_logs_response_ids(self):
        guardrail = ResponsesContractGuardrail(
            guardrail_name="responses-contract-pre",
            event_hook="pre_call",
            default_on=True,
        )
        data = {
            "model": "chatgpt-5",
            "stream": True,
        }
        await guardrail.async_pre_call_hook(
            user_api_key_dict=None,
            cache=None,
            data=data,
            call_type="responses",
        )
        captured = []
        response = {
            "id": "resp_123",
            "previous_response_id": "resp_prev",
            "tools": [{"name": "noop"}],
            "output": [{"call_id": "call_123"}],
        }
        with patch.object(responses_contract_guardrail, "emit_policy_event", side_effect=captured.append):
            out = await guardrail.async_post_call_success_hook(
                data=data,
                user_api_key_dict=None,
                response=response,
            )
        self.assertEqual(out["id"], "resp_123")
        self.assertEqual(captured[0]["event_type"], "policy_result")
        self.assertEqual(captured[0]["response_id"], "resp_123")
        self.assertEqual(captured[0]["previous_response_id"], "resp_prev")
        self.assertEqual(captured[0]["call_ids"], ["call_123"])


class TestEmitPolicyEvent(unittest.TestCase):
    def test_emit_policy_event_writes_jsonl(self):
        trace_path = REPO_ROOT / "services/litellm-orch/tests/_tmp_responses_contract_trace.jsonl"
        try:
            if trace_path.exists():
                trace_path.unlink()
            original = responses_contract_guardrail._TRACE_PATH
            responses_contract_guardrail._TRACE_PATH = trace_path
            responses_contract_guardrail.emit_policy_event({"event_type": "policy_decision", "decision": "normalized"})
            self.assertTrue(trace_path.exists())
            rows = trace_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(json.loads(rows[-1])["decision"], "normalized")
        finally:
            responses_contract_guardrail._TRACE_PATH = original
            if trace_path.exists():
                trace_path.unlink()


if __name__ == "__main__":
    unittest.main()
