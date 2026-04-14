#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path


SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._-]+")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("api_key_assign", re.compile(r"\b(api[_-]?key|token|secret)\b\s*[:=]\s*['\"]?[A-Za-z0-9._-]{12,}")),
    ("hex_blob", re.compile(r"\b[A-Fa-f0-9]{40,}\b")),
    ("private_key_marker", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

SENSITIVE_REF_MARKERS: tuple[str, ...] = (
    ".codex/auth.json",
    ".codex/state_",
    ".sqlite",
    ".sqlite-wal",
    ".sqlite-shm",
    ".codex/cache/",
)


@dataclass
class BuildStats:
    scanned: int = 0
    kept: int = 0
    skipped_before_window: int = 0
    skipped_empty_text: int = 0
    skipped_sensitive_ref: int = 0
    redacted_records: int = 0


def _to_iso_utc(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def _redact_text(text: str) -> tuple[str, list[str]]:
    out = text
    reasons: list[str] = []
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(out):
            reasons.append(name)
            out = pattern.sub(f"[REDACTED_{name.upper()}]", out)
    seen: set[str] = set()
    ordered_reasons: list[str] = []
    for reason in reasons:
        if reason in seen:
            continue
        seen.add(reason)
        ordered_reasons.append(reason)
    return out, ordered_reasons


def _message_id(ts: int, text: str, collision_count: int) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    base = f"{ts}:{digest}"
    if collision_count <= 1:
        return base
    return f"{base}:{collision_count}"


def build_pilot(
    in_path: Path,
    out_path: Path,
    source: str,
    since_days: int,
    max_records: int | None,
    redact: bool,
    dry_run: bool,
) -> dict[str, object]:
    now = datetime.now(tz=UTC)
    cutoff = now - timedelta(days=since_days)
    cutoff_epoch = int(cutoff.timestamp())

    stats = BuildStats()
    collisions: dict[str, dict[str, int]] = defaultdict(dict)

    if not in_path.exists():
        raise FileNotFoundError(f"input file not found: {in_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    writer = None
    if not dry_run:
        writer = out_path.open("w", encoding="utf-8")

    try:
        with in_path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                stats.scanned += 1

                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts_raw = rec.get("ts")
                text_raw = rec.get("text")
                session_id = str(rec.get("session_id", "") or "")

                if ts_raw is None:
                    continue
                try:
                    ts = int(ts_raw)
                except (TypeError, ValueError):
                    continue

                if ts < cutoff_epoch:
                    stats.skipped_before_window += 1
                    continue

                text = str(text_raw or "").strip()
                if not text:
                    stats.skipped_empty_text += 1
                    continue

                text_l = text.lower()
                if any(marker in text_l for marker in SENSITIVE_REF_MARKERS):
                    stats.skipped_sensitive_ref += 1
                    continue

                redaction_reasons: list[str] = []
                if redact:
                    text, redaction_reasons = _redact_text(text)
                    if redaction_reasons:
                        stats.redacted_records += 1

                coll_key = f"{ts}:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}"
                collisions[session_id][coll_key] = collisions[session_id].get(coll_key, 0) + 1
                msg_id = _message_id(ts, text, collisions[session_id][coll_key])

                out_rec = {
                    "source": source,
                    "source_thread_id": session_id,
                    "source_message_id": msg_id,
                    "timestamp": _to_iso_utc(ts),
                    "title": "codex-history",
                    "uri": "",
                    "raw_ref": {
                        "origin": str(in_path),
                        "line_no": line_no,
                        "ts": ts,
                        "redaction_applied": bool(redaction_reasons),
                        "redaction_reasons": redaction_reasons,
                    },
                    "schema_version": "events.v0",
                    "text": text,
                }

                if writer is not None:
                    writer.write(json.dumps(out_rec, ensure_ascii=False) + "\n")
                stats.kept += 1
                if max_records is not None and stats.kept >= max_records:
                    break
    finally:
        if writer is not None:
            writer.close()

    return {
        "ok": True,
        "input": str(in_path),
        "output": str(out_path),
        "source": source,
        "since_days": since_days,
        "max_records": max_records,
        "redact": redact,
        "dry_run": dry_run,
        "stats": {
            "scanned": stats.scanned,
            "kept": stats.kept,
            "skipped_before_window": stats.skipped_before_window,
            "skipped_empty_text": stats.skipped_empty_text,
            "skipped_sensitive_ref": stats.skipped_sensitive_ref,
            "redacted_records": stats.redacted_records,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Codex history pilot corpus for vector-db ingest.")
    parser.add_argument(
        "--in",
        dest="input_path",
        default=str(Path.home() / ".codex" / "history.jsonl"),
        help="Input history.jsonl path (default: ~/.codex/history.jsonl)",
    )
    parser.add_argument("--out", dest="output_path", required=True, help="Output JSONL path")
    parser.add_argument("--since-days", type=int, default=30, help="Include only records from last N days")
    parser.add_argument("--source", default="codex_history_pilot", help="Value for source field")
    parser.add_argument("--max-records", type=int, default=None, help="Optional cap for kept output records")
    parser.add_argument("--no-redact", action="store_true", help="Disable redaction (not recommended)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write output file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_pilot(
        in_path=Path(args.input_path).expanduser(),
        out_path=Path(args.output_path).expanduser(),
        source=args.source,
        since_days=args.since_days,
        max_records=args.max_records,
        redact=not args.no_redact,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
