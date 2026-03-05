import concurrent.futures
import logging
import time
from typing import Any

SLUG = "plansearchtrio"

logger = logging.getLogger(__name__)

DEFAULT_FAST_MODEL = "fast"
DEFAULT_MAIN_MODEL = "main"
DEFAULT_DEEP_MODEL = "deep"

MODE_AUTO = "auto"
MODE_COMPACT = "compact"
MODE_FULL = "full"


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


def _str_param(config: dict[str, Any], key: str, default: str) -> str:
    value = config.get(key, default)
    if not isinstance(value, str):
        return default
    value = value.strip().lower()
    return value if value else default


def _bool_param(config: dict[str, Any], key: str, default: bool) -> bool:
    value = config.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _content_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [_content_to_text(item) for item in value]
        return "".join(part for part in parts if part)
    if isinstance(value, dict):
        for key in ("text", "output_text", "content"):
            if key in value:
                return _content_to_text(value.get(key))
        return ""
    return ""


def _extract_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    first = choices[0]
    message = getattr(first, "message", None)
    if message is None:
        return _content_to_text(getattr(first, "text", ""))
    content = getattr(message, "content", None)
    return _content_to_text(content)


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


def _chat(
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    request_config: dict[str, Any],
    max_tokens: int,
    stage_name: str,
    debug: bool = False,
) -> tuple[str, int]:
    start = time.perf_counter()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    payload.update(_build_call_config(request_config, max_tokens))
    response = client.chat.completions.create(**payload)
    text = _extract_text(response).strip()
    tokens = _extract_completion_tokens(response)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    if debug:
        logger.info(
            "plansearchtrio stage=%s model=%s chars=%s completion_tokens=%s latency_ms=%s",
            stage_name,
            model,
            len(text),
            tokens,
            elapsed_ms,
        )
    return text, tokens


def _chat_resilient(
    client: Any,
    models: list[str],
    system_prompt: str,
    user_prompt: str,
    request_config: dict[str, Any],
    max_tokens: int,
    stage_name: str,
    retries: int,
    min_chars: int,
    debug: bool = False,
) -> tuple[str, int]:
    token_total = 0
    for model in models:
        for attempt in range(1, retries + 2):
            text, tokens = _chat(
                client=client,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                request_config=request_config,
                max_tokens=max_tokens,
                stage_name=stage_name,
                debug=debug,
            )
            token_total += tokens
            if len(text.strip()) >= min_chars:
                return text, token_total
            logger.warning(
                "plansearchtrio empty stage output stage=%s model=%s attempt=%s min_chars=%s chars=%s",
                stage_name,
                model,
                attempt,
                min_chars,
                len(text.strip()),
            )
    return "", token_total


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
    retries: int,
    min_chars: int,
    debug: bool,
) -> tuple[list[str], int]:
    prompt_template = (
        "Task context:\n{query}\n\n"
        "Constraints and success criteria:\n{triage}\n\n"
        "Produce one candidate implementation plan with:"
        " assumptions, steps, risks, verification, and rollback."
    )

    jobs: list[tuple[int, str, str]] = []
    for idx in range(c_fast):
        jobs.append(
            (
                len(jobs),
                fast_model,
                prompt_template.format(query=query, triage=triage) + f"\n\nCandidate ID: fast-{idx + 1}",
            )
        )
    for idx in range(c_main):
        jobs.append(
            (
                len(jobs),
                main_model,
                prompt_template.format(query=query, triage=triage) + f"\n\nCandidate ID: main-{idx + 1}",
            )
        )

    candidates: list[str] = []
    token_total = 0
    ordered: dict[int, str] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _chat_resilient,
                client,
                [model_name],
                system_prompt,
                prompt,
                request_config,
                candidate_budget,
                f"candidate-{job_index}",
                retries,
                min_chars,
                debug,
            ): job_index
            for job_index, model_name, prompt in jobs
        }
        for future in concurrent.futures.as_completed(futures):
            job_index = futures[future]
            text, tokens = future.result()
            if text:
                ordered[job_index] = text
            token_total += tokens

    for job_index in sorted(ordered):
        candidates.append(ordered[job_index])

    return candidates, token_total


def _elapsed_ms(start_time: float) -> int:
    return int((time.perf_counter() - start_time) * 1000)


def _within_budget(start_time: float, latency_budget_ms: int) -> bool:
    return _elapsed_ms(start_time) <= latency_budget_ms


def _fallback_final_response(
    client: Any,
    system_prompt: str,
    initial_query: str,
    config: dict[str, Any],
    main_model: str,
    deep_model: str,
    stage_retries: int,
    requested_budget: int,
    debug: bool,
) -> tuple[str, int]:
    fallback_budget = _stage_budget(config, "plansearchtrio_budget_fallback", min(768, requested_budget))
    fallback_prompt = (
        "Produce a concise but complete implementation plan with risks and rollback.\n\n"
        f"Task:\n{initial_query}"
    )
    text, tokens = _chat_resilient(
        client=client,
        models=[main_model, deep_model],
        system_prompt=system_prompt,
        user_prompt=fallback_prompt,
        request_config=config,
        max_tokens=fallback_budget,
        stage_name="fallback",
        retries=stage_retries,
        min_chars=8,
        debug=debug,
    )
    if text:
        return text, tokens
    return (
        "I could not complete the full trio pipeline for this request. "
        "Here is a compact fallback plan: clarify scope, define constraints, stage rollout, and include rollback checks.",
        tokens,
    )


def run(system_prompt: str, initial_query: str, client=None, model=None, request_config=None):
    if client is None:
        raise ValueError("plansearchtrio requires a configured provider client")

    start_time = time.perf_counter()
    config: dict[str, Any] = dict(request_config or {})
    fast_model, main_model, deep_model = _pick_models(config, model)

    mode = _str_param(config, "plansearchtrio_mode", MODE_AUTO)
    if mode not in {MODE_AUTO, MODE_COMPACT, MODE_FULL}:
        mode = MODE_AUTO

    requested_budget = _requested_token_budget(config)

    # Compact defaults are used for auto unless explicitly overridden.
    if mode in {MODE_AUTO, MODE_COMPACT}:
        compact_defaults: dict[str, Any] = {
            "plansearchtrio_candidates_fast": 1,
            "plansearchtrio_candidates_main": 1,
            "plansearchtrio_keep": 1,
            "plansearchtrio_repair_rounds": 0,
            "plansearchtrio_stage_retries": 0,
            "plansearchtrio_budget_triage": min(96, requested_budget),
            "plansearchtrio_budget_candidate": min(128, requested_budget),
            "plansearchtrio_budget_critique": min(160, requested_budget),
            "plansearchtrio_budget_synthesis": min(512, requested_budget),
            "plansearchtrio_budget_verify": min(64, requested_budget),
            "plansearchtrio_budget_repair": min(256, requested_budget),
        }
        for key, value in compact_defaults.items():
            config.setdefault(key, value)

    c_fast = _int_param(config, "plansearchtrio_candidates_fast", 2, 1, 8)
    c_main = _int_param(config, "plansearchtrio_candidates_main", 1, 1, 8)
    k_keep = _int_param(config, "plansearchtrio_keep", 2, 1, 6)
    repair_rounds = _int_param(config, "plansearchtrio_repair_rounds", 1, 0, 3)
    max_workers = _int_param(config, "plansearchtrio_max_workers", 3, 1, 8)
    stage_retries = _int_param(config, "plansearchtrio_stage_retries", 1, 0, 3)
    min_stage_chars = _int_param(config, "plansearchtrio_min_stage_chars", 8, 1, 512)
    fallback_on_empty = _bool_param(config, "plansearchtrio_fallback_on_empty", True)
    latency_budget_ms = _int_param(config, "plansearchtrio_latency_budget_ms", 17000, 1000, 300000)
    debug = _bool_param(config, "plansearchtrio_debug", False)

    default_enable_critique = mode == MODE_FULL
    default_enable_repair = mode == MODE_FULL
    enable_critique = _bool_param(config, "plansearchtrio_enable_critique", default_enable_critique)
    enable_verify = _bool_param(config, "plansearchtrio_enable_verify", True)
    enable_repair = _bool_param(config, "plansearchtrio_enable_repair", default_enable_repair)

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
    triage, tokens = _chat_resilient(
        client=client,
        models=[fast_model],
        system_prompt=system_prompt,
        user_prompt=triage_prompt,
        request_config=config,
        max_tokens=budget_triage,
        stage_name="triage",
        retries=stage_retries,
        min_chars=min_stage_chars,
        debug=debug,
    )
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
        retries=stage_retries,
        min_chars=min_stage_chars,
        debug=debug,
    )
    total_tokens += tokens

    if not candidates:
        fallback_text, fallback_tokens = _fallback_final_response(
            client=client,
            system_prompt=system_prompt,
            initial_query=initial_query,
            config=config,
            main_model=main_model,
            deep_model=deep_model,
            stage_retries=stage_retries,
            requested_budget=requested_budget,
            debug=debug,
        )
        return fallback_text, total_tokens + fallback_tokens

    critique = ""
    if enable_critique and _within_budget(start_time, latency_budget_ms):
        critique_prompt = (
            "Evaluate candidates against constraints. Return top candidates and short rationale.\n\n"
            f"Constraints:\n{triage}\n\n"
            "Candidates:\n"
            + "\n\n".join(f"Candidate {idx + 1}:\n{text}" for idx, text in enumerate(candidates))
        )
        critique, tokens = _chat_resilient(
            client=client,
            models=[main_model],
            system_prompt=system_prompt,
            user_prompt=critique_prompt,
            request_config=config,
            max_tokens=budget_critique,
            stage_name="critique",
            retries=stage_retries,
            min_chars=min_stage_chars,
            debug=debug,
        )
        total_tokens += tokens

    selected_candidates = candidates[:k_keep]
    synthesis_prompt = (
        "Produce the final response using the best candidates and critique.\n"
        "Output: coherent plan, implementation details, risks, rollback.\n\n"
        f"Task:\n{initial_query}\n\n"
        f"Constraints:\n{triage}\n\n"
        f"Critique:\n{critique or 'N/A'}\n\n"
        "Top candidates:\n"
        + "\n\n".join(f"Candidate {idx + 1}:\n{text}" for idx, text in enumerate(selected_candidates))
    )

    synthesis_models = [deep_model]
    if fallback_on_empty and main_model not in synthesis_models:
        synthesis_models.append(main_model)
    final_text, tokens = _chat_resilient(
        client=client,
        models=synthesis_models,
        system_prompt=system_prompt,
        user_prompt=synthesis_prompt,
        request_config=config,
        max_tokens=budget_synthesis,
        stage_name="synthesis",
        retries=stage_retries,
        min_chars=min_stage_chars,
        debug=debug,
    )
    total_tokens += tokens

    if not final_text:
        fallback_text, fallback_tokens = _fallback_final_response(
            client=client,
            system_prompt=system_prompt,
            initial_query=initial_query,
            config=config,
            main_model=main_model,
            deep_model=deep_model,
            stage_retries=stage_retries,
            requested_budget=requested_budget,
            debug=debug,
        )
        return fallback_text, total_tokens + fallback_tokens

    def _make_verifier_prompt(current_final_text: str) -> str:
        return (
            "Check whether the final response violates constraints or misses rollback/checks. "
            "Reply with PASS or REPAIR, then a brief reason.\n\n"
            f"Constraints:\n{triage}\n\n"
            f"Final response:\n{current_final_text}"
        )

    verdict = "PASS"
    if enable_verify and _within_budget(start_time, latency_budget_ms):
        verdict, tokens = _chat_resilient(
            client=client,
            models=[fast_model],
            system_prompt=system_prompt,
            user_prompt=_make_verifier_prompt(final_text),
            request_config=config,
            max_tokens=budget_verify,
            stage_name="verify",
            retries=stage_retries,
            min_chars=4,
            debug=debug,
        )
        total_tokens += tokens
        if not verdict:
            verdict = "PASS: verifier returned empty verdict"

    round_index = 0
    while (
        enable_repair
        and _within_budget(start_time, latency_budget_ms)
        and verdict.upper().startswith("REPAIR")
        and round_index < repair_rounds
    ):
        round_index += 1
        repair_prompt = (
            "Given the verifier feedback, produce precise fix instructions.\n\n"
            f"Verifier feedback:\n{verdict}\n\n"
            f"Current response:\n{final_text}"
        )
        repair_instructions, tokens = _chat_resilient(
            client=client,
            models=[main_model],
            system_prompt=system_prompt,
            user_prompt=repair_prompt,
            request_config=config,
            max_tokens=budget_repair,
            stage_name="repair-instructions",
            retries=stage_retries,
            min_chars=min_stage_chars,
            debug=debug,
        )
        total_tokens += tokens
        if not repair_instructions:
            break

        rewrite_prompt = (
            "Revise the response using these fix instructions. Keep it complete and consistent.\n\n"
            f"Fix instructions:\n{repair_instructions}\n\n"
            f"Current response:\n{final_text}"
        )
        final_text, tokens = _chat_resilient(
            client=client,
            models=synthesis_models,
            system_prompt=system_prompt,
            user_prompt=rewrite_prompt,
            request_config=config,
            max_tokens=budget_synthesis,
            stage_name="rewrite",
            retries=stage_retries,
            min_chars=min_stage_chars,
            debug=debug,
        )
        total_tokens += tokens
        if not final_text:
            fallback_text, fallback_tokens = _fallback_final_response(
                client=client,
                system_prompt=system_prompt,
                initial_query=initial_query,
                config=config,
                main_model=main_model,
                deep_model=deep_model,
                stage_retries=stage_retries,
                requested_budget=requested_budget,
                debug=debug,
            )
            return fallback_text, total_tokens + fallback_tokens

        if enable_verify and _within_budget(start_time, latency_budget_ms):
            verdict, tokens = _chat_resilient(
                client=client,
                models=[fast_model],
                system_prompt=system_prompt,
                user_prompt=_make_verifier_prompt(final_text),
                request_config=config,
                max_tokens=budget_verify,
                stage_name="verify",
                retries=stage_retries,
                min_chars=4,
                debug=debug,
            )
            total_tokens += tokens
            if not verdict:
                verdict = "PASS: verifier returned empty verdict"
        else:
            verdict = "PASS"

    logger.info(
        "plansearchtrio complete mode=%s fast=%s main=%s deep=%s c_fast=%s c_main=%s keep=%s repair_rounds=%s elapsed_ms=%s",
        mode,
        fast_model,
        main_model,
        deep_model,
        c_fast,
        c_main,
        k_keep,
        repair_rounds,
        _elapsed_ms(start_time),
    )
    return final_text, total_tokens
