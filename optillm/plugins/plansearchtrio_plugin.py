import concurrent.futures
import logging
from typing import Any

SLUG = "plansearchtrio"

logger = logging.getLogger(__name__)

DEFAULT_FAST_MODEL = "fast"
DEFAULT_MAIN_MODEL = "main"
DEFAULT_DEEP_MODEL = "deep"


def _int_param(config: dict[str, Any], key: str, default: int, minimum: int, maximum: int) -> int:
    value = config.get(key, default)
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _stage_budget(config: dict[str, Any], key: str, fallback: int) -> int:
    return _int_param(config, key, fallback, 32, 32768)

def _requested_token_budget(config: dict[str, Any]) -> int:
    raw = config.get("max_completion_tokens", config.get("max_tokens", 512))
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        parsed = 512
    return max(32, min(4096, parsed))


def _pick_models(config: dict[str, Any], requested_model: str | None) -> tuple[str, str, str]:
    fast = str(config.get("plansearchtrio_fast_model") or DEFAULT_FAST_MODEL)
    main = str(config.get("plansearchtrio_main_model") or DEFAULT_MAIN_MODEL)
    deep = str(config.get("plansearchtrio_deep_model") or requested_model or DEFAULT_DEEP_MODEL)
    return fast, main, deep


def _extract_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    if message is None:
        return ""
    content = getattr(message, "content", None)
    return content if isinstance(content, str) else ""


def _extract_completion_tokens(response: Any) -> int:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0
    tokens = getattr(usage, "completion_tokens", 0)
    return int(tokens) if isinstance(tokens, int) else 0


def _build_call_config(config: dict[str, Any], max_tokens: int) -> dict[str, Any]:
    payload: dict[str, Any] = {"max_tokens": max_tokens, "stream": False}
    for key in ("temperature", "top_p", "frequency_penalty", "presence_penalty"):
        if key in config:
            payload[key] = config[key]
    if "response_format" in config:
        payload["response_format"] = config["response_format"]
    return payload


def _chat(client: Any, model: str, system_prompt: str, user_prompt: str, request_config: dict[str, Any], max_tokens: int) -> tuple[str, int]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    payload.update(_build_call_config(request_config, max_tokens))
    response = client.chat.completions.create(**payload)
    return _extract_text(response).strip(), _extract_completion_tokens(response)


def _parallel_candidates(
    client: Any,
    request_config: dict[str, Any],
    system_prompt: str,
    query: str,
    triage: str,
    fast_model: str,
    main_model: str,
    candidate_budget: int,
    c_fast: int,
    c_main: int,
    max_workers: int,
) -> tuple[list[str], int]:
    prompt_template = (
        "Task context:\n{query}\n\n"
        "Constraints and success criteria:\n{triage}\n\n"
        "Produce one candidate implementation plan with:"
        " assumptions, steps, risks, verification, and rollback."
    )

    jobs: list[tuple[str, str]] = []
    for idx in range(c_fast):
        jobs.append((fast_model, prompt_template.format(query=query, triage=triage) + f"\n\nCandidate ID: fast-{idx + 1}"))
    for idx in range(c_main):
        jobs.append((main_model, prompt_template.format(query=query, triage=triage) + f"\n\nCandidate ID: main-{idx + 1}"))

    candidates: list[str] = []
    token_total = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _chat,
                client,
                model_name,
                system_prompt,
                prompt,
                request_config,
                candidate_budget,
            )
            for model_name, prompt in jobs
        ]
        for future in concurrent.futures.as_completed(futures):
            text, tokens = future.result()
            if text:
                candidates.append(text)
            token_total += tokens

    return candidates, token_total


def run(system_prompt: str, initial_query: str, client=None, model=None, request_config=None):
    if client is None:
        raise ValueError("plansearchtrio requires a configured provider client")

    config: dict[str, Any] = dict(request_config or {})
    fast_model, main_model, deep_model = _pick_models(config, model)

    c_fast = _int_param(config, "plansearchtrio_candidates_fast", 2, 1, 8)
    c_main = _int_param(config, "plansearchtrio_candidates_main", 1, 1, 8)
    k_keep = _int_param(config, "plansearchtrio_keep", 2, 1, 6)
    repair_rounds = _int_param(config, "plansearchtrio_repair_rounds", 1, 0, 3)
    max_workers = _int_param(config, "plansearchtrio_max_workers", 3, 1, 8)
    requested_budget = _requested_token_budget(config)

    budget_triage = _stage_budget(config, "plansearchtrio_budget_triage", min(256, requested_budget))
    budget_candidate = _stage_budget(config, "plansearchtrio_budget_candidate", min(384, requested_budget))
    budget_critique = _stage_budget(config, "plansearchtrio_budget_critique", min(512, requested_budget))
    budget_synthesis = _stage_budget(config, "plansearchtrio_budget_synthesis", min(1024, requested_budget))
    budget_verify = _stage_budget(config, "plansearchtrio_budget_verify", min(192, requested_budget))
    budget_repair = _stage_budget(config, "plansearchtrio_budget_repair", min(512, requested_budget))

    total_tokens = 0

    triage_prompt = (
        "Summarize this task into: requirements, constraints, acceptance checks, and unknowns.\n\n"
        f"Task:\n{initial_query}"
    )
    triage, tokens = _chat(client, fast_model, system_prompt, triage_prompt, config, budget_triage)
    total_tokens += tokens

    candidates, tokens = _parallel_candidates(
        client=client,
        request_config=config,
        system_prompt=system_prompt,
        query=initial_query,
        triage=triage,
        fast_model=fast_model,
        main_model=main_model,
        candidate_budget=budget_candidate,
        c_fast=c_fast,
        c_main=c_main,
        max_workers=max_workers,
    )
    total_tokens += tokens

    if not candidates:
        return "", total_tokens

    critique_prompt = (
        "Evaluate candidates against constraints. Return top candidates and short rationale.\n\n"
        f"Constraints:\n{triage}\n\n"
        "Candidates:\n"
        + "\n\n".join(f"Candidate {idx + 1}:\n{text}" for idx, text in enumerate(candidates))
    )
    critique, tokens = _chat(client, main_model, system_prompt, critique_prompt, config, budget_critique)
    total_tokens += tokens

    selected_candidates = candidates[:k_keep]
    synthesis_prompt = (
        "Produce the final response using the best candidates and critique.\n"
        "Output: coherent plan, implementation details, risks, rollback.\n\n"
        f"Task:\n{initial_query}\n\n"
        f"Constraints:\n{triage}\n\n"
        f"Critique:\n{critique}\n\n"
        "Top candidates:\n"
        + "\n\n".join(f"Candidate {idx + 1}:\n{text}" for idx, text in enumerate(selected_candidates))
    )
    final_text, tokens = _chat(client, deep_model, system_prompt, synthesis_prompt, config, budget_synthesis)
    total_tokens += tokens

    def _make_verifier_prompt(current_final_text: str) -> str:
        return (
            "Check whether the final response violates constraints or misses rollback/checks. "
            "Reply with PASS or REPAIR, then a brief reason.\n\n"
            f"Constraints:\n{triage}\n\n"
            f"Final response:\n{current_final_text}"
        )

    verdict, tokens = _chat(
        client,
        fast_model,
        system_prompt,
        _make_verifier_prompt(final_text),
        config,
        budget_verify,
    )
    total_tokens += tokens

    round_index = 0
    while verdict.upper().startswith("REPAIR") and round_index < repair_rounds:
        round_index += 1
        repair_prompt = (
            "Given the verifier feedback, produce precise fix instructions.\n\n"
            f"Verifier feedback:\n{verdict}\n\n"
            f"Current response:\n{final_text}"
        )
        repair_instructions, tokens = _chat(client, main_model, system_prompt, repair_prompt, config, budget_repair)
        total_tokens += tokens

        rewrite_prompt = (
            "Revise the response using these fix instructions. Keep it complete and consistent.\n\n"
            f"Fix instructions:\n{repair_instructions}\n\n"
            f"Current response:\n{final_text}"
        )
        final_text, tokens = _chat(client, deep_model, system_prompt, rewrite_prompt, config, budget_synthesis)
        total_tokens += tokens

        verdict, tokens = _chat(
            client,
            fast_model,
            system_prompt,
            _make_verifier_prompt(final_text),
            config,
            budget_verify,
        )
        total_tokens += tokens

    logger.info(
        "plansearchtrio complete fast=%s main=%s deep=%s c_fast=%s c_main=%s keep=%s repair_rounds=%s",
        fast_model,
        main_model,
        deep_model,
        c_fast,
        c_main,
        k_keep,
        repair_rounds,
    )
    return final_text, total_tokens
