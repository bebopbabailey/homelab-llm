from __future__ import annotations

from dataclasses import dataclass
import shlex

VALID_FIXTURE_IDS = frozenset({"G01", "G02", "S01", "S02", "S03", "S04"})
SPECIALIZED_PREFIX = "/specialized"
PI_PREFIX = "/pi"


@dataclass(frozen=True)
class RouteDecision:
    mission_mode: str
    route_decision: str
    route_reason: str
    fixture_id: str | None = None
    mission_text: str = ""
    pi_temperature: float | None = None
    pi_max_tokens: int | None = None


def decide_route(latest_text: str) -> RouteDecision:
    text = latest_text.strip()
    if not text:
        return RouteDecision(
            mission_mode="ordinary",
            route_decision="ordinary-placeholder",
            route_reason="empty input defaults to the ordinary placeholder path",
            mission_text="",
        )
    if text == PI_PREFIX or text.startswith(f"{PI_PREFIX} "):
        return _decide_pi_route(text)
    if not (text == SPECIALIZED_PREFIX or text.startswith(f"{SPECIALIZED_PREFIX} ")):
        return RouteDecision(
            mission_mode="ordinary",
            route_decision="ordinary-placeholder",
            route_reason="message does not request the specialized runtime contract",
            mission_text=text,
        )
    parts = text.split(None, 2)
    if len(parts) < 3:
        return RouteDecision(
            mission_mode="specialized",
            route_decision="out-of-scope",
            route_reason="specialized missions must use '/specialized <fixture-id> <mission text>'",
            mission_text=text,
        )
    _, fixture_id, mission_text = parts
    if fixture_id not in VALID_FIXTURE_IDS:
        return RouteDecision(
            mission_mode="specialized",
            route_decision="out-of-scope",
            route_reason=f"unsupported specialized fixture '{fixture_id}'",
            mission_text=mission_text,
        )
    lowered = mission_text.lower()
    if any(token in lowered for token in ("tool", "tool_choice", "stream", "response_format", "responses")):
        return RouteDecision(
            mission_mode="specialized",
            route_decision="out-of-scope",
            route_reason="phase 4 specialized missions reject tools, streaming, and structured-output requests",
            mission_text=mission_text,
        )
    return RouteDecision(
        mission_mode="specialized",
        route_decision="specialized-runtime",
        route_reason=f"specialized command matched validated fixture family {fixture_id}",
        fixture_id=fixture_id,
        mission_text=mission_text,
    )


def _decide_pi_route(text: str) -> RouteDecision:
    raw_args = text[len(PI_PREFIX):].strip()
    if not raw_args:
        return RouteDecision(
            mission_mode="pi",
            route_decision="out-of-scope",
            route_reason="Pi scratch runs must use '/pi <task text>'",
            mission_text="",
        )
    try:
        tokens = shlex.split(raw_args)
    except ValueError as exc:
        return RouteDecision(
            mission_mode="pi",
            route_decision="out-of-scope",
            route_reason=f"could not parse /pi arguments: {exc}",
            mission_text=raw_args,
        )

    temperature: float | None = None
    max_tokens: int | None = None
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token not in {"--temperature", "--temp", "--max-tokens", "--max_tokens"}:
            break
        if index + 1 >= len(tokens):
            return RouteDecision(
                mission_mode="pi",
                route_decision="out-of-scope",
                route_reason=f"{token} requires a value",
                mission_text=raw_args,
            )
        value = tokens[index + 1]
        if token in {"--temperature", "--temp"}:
            try:
                temperature = float(value)
            except ValueError:
                return RouteDecision(
                    mission_mode="pi",
                    route_decision="out-of-scope",
                    route_reason="Pi temperature must be a number",
                    mission_text=raw_args,
                )
            if not 0 <= temperature <= 2:
                return RouteDecision(
                    mission_mode="pi",
                    route_decision="out-of-scope",
                    route_reason="Pi temperature must be between 0 and 2",
                    mission_text=raw_args,
                )
        else:
            try:
                max_tokens = int(value)
            except ValueError:
                return RouteDecision(
                    mission_mode="pi",
                    route_decision="out-of-scope",
                    route_reason="Pi max tokens must be an integer",
                    mission_text=raw_args,
                )
            if not 256 <= max_tokens <= 16384:
                return RouteDecision(
                    mission_mode="pi",
                    route_decision="out-of-scope",
                    route_reason="Pi max tokens must be between 256 and 16384",
                    mission_text=raw_args,
                )
        index += 2

    task = " ".join(tokens[index:]).strip()
    if not task:
        return RouteDecision(
            mission_mode="pi",
            route_decision="out-of-scope",
            route_reason="Pi scratch runs require task text after any knobs",
            mission_text=raw_args,
        )
    return RouteDecision(
        mission_mode="pi",
        route_decision="pi-scratch-run",
        route_reason="Pi scratch-run command matched",
        mission_text=task,
        pi_temperature=temperature,
        pi_max_tokens=max_tokens,
    )
