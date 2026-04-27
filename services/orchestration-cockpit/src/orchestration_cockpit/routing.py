from __future__ import annotations

from dataclasses import dataclass

VALID_FIXTURE_IDS = frozenset({"G01", "G02", "S01", "S02", "S03", "S04"})
SPECIALIZED_PREFIX = "/specialized"


@dataclass(frozen=True)
class RouteDecision:
    mission_mode: str
    route_decision: str
    route_reason: str
    fixture_id: str | None = None
    mission_text: str = ""


def decide_route(latest_text: str) -> RouteDecision:
    text = latest_text.strip()
    if not text:
        return RouteDecision(
            mission_mode="ordinary",
            route_decision="ordinary-placeholder",
            route_reason="empty input defaults to the ordinary placeholder path",
            mission_text="",
        )
    if not text.startswith(SPECIALIZED_PREFIX):
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
