"""OptiLLM-compatible decode-time controls for an MLX-LM experimental server fork.

This module is intentionally self-contained so the patch surface in ``mlx_lm/server.py``
stays small and rebase-friendly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, Iterable, Optional, Tuple


DECODE_FROM_APPROACH: Dict[str, str] = {
    "entropy": "entropy_decoding",
    "entropy_decoding": "entropy_decoding",
    "cot_decoding": "cot_decoding",
    "deepconf": "deepconf",
    "thinkdeeper": "thinkdeeper",
    "autothink": "autothink",
}

SUPPORTED_TECHNIQUES = {
    "default",
    "entropy_decoding",
}


@dataclass(frozen=True)
class DecodingArguments:
    """Per-request decoding configuration normalized from request body fields."""

    technique: str = "default"
    return_metadata: bool = False
    params: Dict[str, Any] = field(default_factory=dict)

    def batch_signature(self) -> Tuple[Any, ...]:
        """Stable value used to partition concurrent batches by decode behavior."""
        return (
            self.technique,
            self.return_metadata,
            tuple(sorted((k, _normalize_scalar(v)) for k, v in self.params.items())),
        )


@dataclass
class EntropyState:
    """Mutable state captured by a logits processor for one request."""

    base_temperature: float
    target_entropy: float
    alpha: float
    min_temperature: float
    max_temperature: float
    history_limit: int
    steps: int = 0
    entropy_sum: float = 0.0
    entropy_max: float = 0.0
    temp_min: float = float("inf")
    temp_max: float = float("-inf")
    _entropy_history: list[float] = field(default_factory=list)

    def record(self, entropy: float, temperature: float) -> None:
        self.steps += 1
        self.entropy_sum += entropy
        self.entropy_max = max(self.entropy_max, entropy)
        self.temp_min = min(self.temp_min, temperature)
        self.temp_max = max(self.temp_max, temperature)

        if self.history_limit > 0 and len(self._entropy_history) < self.history_limit:
            self._entropy_history.append(entropy)

    def summary(self) -> Dict[str, Any]:
        mean_entropy = self.entropy_sum / self.steps if self.steps else 0.0
        entropy_p95 = _percentile(self._entropy_history, 95.0)
        if entropy_p95 is None:
            entropy_p95 = self.entropy_max

        return {
            "steps": self.steps,
            "entropy_mean": round(mean_entropy, 6),
            "entropy_p95": round(float(entropy_p95), 6),
            "entropy_max": round(self.entropy_max, 6),
            "temperature_min": round(self.temp_min if self.steps else self.base_temperature, 6),
            "temperature_max": round(self.temp_max if self.steps else self.base_temperature, 6),
        }


def resolve_decoding_technique(
    decoding: Optional[str],
    optillm_approach: Optional[str],
) -> str:
    """Resolve final technique selector with OptiLLM-compatible precedence.

    Precedence:
    1. explicit ``decoding``
    2. ``optillm_approach`` if it names a decode-time technique
    3. ``default``
    """
    if decoding is not None:
        if not isinstance(decoding, str):
            raise ValueError("decoding must be a string")
        value = decoding.strip().lower()
        return DECODE_FROM_APPROACH.get(value, value)

    if isinstance(optillm_approach, str):
        for slug in optillm_approach.split("|"):
            value = slug.strip().lower()
            mapped = DECODE_FROM_APPROACH.get(value)
            if mapped is not None:
                return mapped

    return "default"


def resolve_decoding_arguments(
    body: Dict[str, Any],
    allow_experimental: bool,
) -> DecodingArguments:
    """Normalize decode-time request fields into ``DecodingArguments``."""
    return_metadata = body.get("return_decoding_metadata", False)
    if not isinstance(return_metadata, bool):
        raise ValueError("return_decoding_metadata must be a boolean")

    technique = resolve_decoding_technique(
        body.get("decoding"),
        body.get("optillm_approach"),
    )

    if technique not in SUPPORTED_TECHNIQUES:
        supported = ", ".join(sorted(SUPPORTED_TECHNIQUES))
        raise ValueError(
            f"decoding technique '{technique}' is not implemented in this server patch; "
            f"supported: {supported}"
        )

    if technique != "default" and not allow_experimental:
        raise ValueError(
            "decode-time techniques are disabled; launch with --enable-optillm-decoding"
        )

    if technique == "default":
        return DecodingArguments("default", return_metadata, {})

    raw_params = body.get("decoding_params", {})
    if raw_params is None:
        raw_params = {}
    if not isinstance(raw_params, dict):
        raise ValueError("decoding_params must be an object")

    base_temp = _as_float(body.get("temperature", 0.7), "temperature")
    if base_temp <= 0:
        base_temp = 0.7

    params = {
        "base_temperature": base_temp,
        "entropy_target": _as_float(
            _resolve_param(raw_params, body, "entropy_target", 2.6),
            "entropy_target",
        ),
        "entropy_alpha": _as_float(
            _resolve_param(raw_params, body, "entropy_alpha", 0.35),
            "entropy_alpha",
        ),
        "entropy_temp_min": _as_float(
            _resolve_param(raw_params, body, "entropy_temp_min", 0.2),
            "entropy_temp_min",
        ),
        "entropy_temp_max": _as_float(
            _resolve_param(raw_params, body, "entropy_temp_max", 1.1),
            "entropy_temp_max",
        ),
        "entropy_history_limit": _as_int(
            _resolve_param(raw_params, body, "entropy_history_limit", 512),
            "entropy_history_limit",
        ),
    }

    if params["entropy_alpha"] < 0:
        raise ValueError("entropy_alpha must be >= 0")
    if params["entropy_temp_min"] <= 0:
        raise ValueError("entropy_temp_min must be > 0")
    if params["entropy_temp_max"] <= 0:
        raise ValueError("entropy_temp_max must be > 0")
    if params["entropy_temp_min"] > params["entropy_temp_max"]:
        raise ValueError("entropy_temp_min must be <= entropy_temp_max")
    if params["entropy_history_limit"] < 0:
        raise ValueError("entropy_history_limit must be >= 0")

    return DecodingArguments(technique, return_metadata, params)


def compute_entropy_from_probabilities(probabilities: Iterable[float]) -> float:
    """Shannon entropy over a normalized probability vector."""
    entropy = 0.0
    total = 0.0
    for probability in probabilities:
        total += probability
        if probability > 0:
            entropy -= probability * math.log(probability)

    if total <= 0:
        return 0.0

    return entropy


def compute_adaptive_temperature(
    *,
    base_temperature: float,
    entropy: float,
    target_entropy: float,
    alpha: float,
    min_temperature: float,
    max_temperature: float,
) -> float:
    """Entropy-guided temperature modulation used by entropy decoding."""
    raw = base_temperature * math.exp(-alpha * (entropy - target_entropy))
    return min(max(raw, min_temperature), max_temperature)


def make_decoding_logits_processor(
    decoding: DecodingArguments,
) -> Tuple[Optional[Any], Optional[EntropyState]]:
    """Create a logits processor + state for the selected technique."""
    if decoding.technique == "default":
        return None, None

    if decoding.technique != "entropy_decoding":
        raise ValueError(f"unsupported decoding technique: {decoding.technique}")

    try:
        import mlx.core as mx
    except ImportError as exc:
        raise RuntimeError("mlx is required for entropy_decoding") from exc

    params = decoding.params
    state = EntropyState(
        base_temperature=float(params["base_temperature"]),
        target_entropy=float(params["entropy_target"]),
        alpha=float(params["entropy_alpha"]),
        min_temperature=float(params["entropy_temp_min"]),
        max_temperature=float(params["entropy_temp_max"]),
        history_limit=int(params["entropy_history_limit"]),
    )

    # Fast path when metadata is not requested: keep math on-device and avoid
    # per-token host sync.
    if not decoding.return_metadata:
        base_temp = mx.array(state.base_temperature)
        target_entropy = mx.array(state.target_entropy)
        alpha = mx.array(state.alpha)
        min_temp = mx.array(state.min_temperature)
        max_temp = mx.array(state.max_temperature)

        def entropy_processor(_, logits):
            row = logits[0]
            entropy = _entropy_from_logits_mx(mx, row)
            effective_temp = base_temp * mx.exp(-alpha * (entropy - target_entropy))
            effective_temp = mx.clip(effective_temp, min_temp, max_temp)
            return logits / effective_temp

        return entropy_processor, None

    def entropy_processor(_, logits):
        # ``logits`` shape: [batch, vocab]; entropy is computed per request row.
        row = logits[0]
        entropy = float(_entropy_from_logits_mx(mx, row).item())

        effective_temp = compute_adaptive_temperature(
            base_temperature=state.base_temperature,
            entropy=entropy,
            target_entropy=state.target_entropy,
            alpha=state.alpha,
            min_temperature=state.min_temperature,
            max_temperature=state.max_temperature,
        )

        state.record(entropy, effective_temp)
        return logits / effective_temp

    return entropy_processor, state


def build_decoding_metadata(
    decoding: DecodingArguments,
    state: Optional[EntropyState],
    resolved_model: str,
) -> Optional[Dict[str, Any]]:
    """Return compact metadata payload if the request opted in."""
    if not decoding.return_metadata:
        return None

    payload: Dict[str, Any] = {
        "technique": decoding.technique,
        "resolved_model": resolved_model,
    }

    if decoding.technique == "entropy_decoding" and state is not None:
        payload.update(state.summary())

    return payload


def _as_float(value: Any, field_name: str) -> float:
    if not isinstance(value, (float, int)):
        raise ValueError(f"{field_name} must be numeric")
    return float(value)


def _as_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _resolve_param(
    decoding_params: Dict[str, Any],
    body: Dict[str, Any],
    key: str,
    default: Any,
) -> Any:
    if key in decoding_params:
        return decoding_params[key]
    return body.get(key, default)


def _entropy_from_logits_mx(mx: Any, row: Any) -> Any:
    """Exact entropy from logits using a stable log-sum-exp form."""
    log_z = mx.logsumexp(row, axis=-1)
    probabilities = mx.exp(row - log_z)
    return log_z - mx.sum(probabilities * row)


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 8)
    return value


def _percentile(values: list[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return values[0]

    sorted_values = sorted(values)
    rank = (percentile / 100.0) * (len(sorted_values) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)

    if lower == upper:
        return sorted_values[int(rank)]

    lower_value = sorted_values[lower]
    upper_value = sorted_values[upper]
    fraction = rank - lower
    return lower_value + (upper_value - lower_value) * fraction
