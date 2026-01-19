#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ALLOWED_KINDS = {"model", "callable"}
ALLOWED_INVOKE = {"openai-chat", "openai-embeddings", "mcp-tool", "http-get", "http-post"}
ALLOWED_MANAGED_BY = {"systemd", "launchd", "docker", "manual", "external"}

REQUIRED_FIELDS = {
    "handle",
    "kind",
    "invoke",
    "managed_by",
    "endpoint_ref",
    "selector",
}
OPTIONAL_FIELDS = {"notes"}
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


def canonical_selector(selector):
    if selector is None:
        return "null"
    return json.dumps(selector, sort_keys=True, separators=(",", ":"))


def error(errors, lineno, field, message):
    errors.append(f"line {lineno}: {field}: {message}")


def validate_row(row, lineno, errors):
    if not isinstance(row, dict):
        error(errors, lineno, "row", "must be a JSON object")
        return None

    extra = set(row.keys()) - ALLOWED_FIELDS
    missing = REQUIRED_FIELDS - set(row.keys())
    if extra:
        error(errors, lineno, "row", f"unexpected fields: {sorted(extra)}")
    if missing:
        error(errors, lineno, "row", f"missing required fields: {sorted(missing)}")

    handle = row.get("handle")
    if not isinstance(handle, str) or not handle:
        error(errors, lineno, "handle", "must be a non-empty string")
    elif any(ch for ch in handle if not (ch.islower() or ch.isdigit() or ch == "-")):
        error(errors, lineno, "handle", "must be lowercase letters, digits, or dashes only")

    kind = row.get("kind")
    if kind not in ALLOWED_KINDS:
        error(errors, lineno, "kind", f"must be one of {sorted(ALLOWED_KINDS)}")

    invoke = row.get("invoke")
    if invoke not in ALLOWED_INVOKE:
        error(errors, lineno, "invoke", f"must be one of {sorted(ALLOWED_INVOKE)}")

    managed_by = row.get("managed_by")
    if managed_by not in ALLOWED_MANAGED_BY:
        error(errors, lineno, "managed_by", f"must be one of {sorted(ALLOWED_MANAGED_BY)}")

    endpoint_ref = row.get("endpoint_ref")
    if not isinstance(endpoint_ref, str) or not endpoint_ref:
        error(errors, lineno, "endpoint_ref", "must be a non-empty string")

    selector = row.get("selector")
    if selector is not None and not isinstance(selector, dict):
        error(errors, lineno, "selector", "must be null or an object")
    if isinstance(selector, dict):
        for key, value in selector.items():
            if isinstance(value, str):
                if key == "model" and (
                    (isinstance(handle, str) and handle.startswith("opt-"))
                    or (isinstance(endpoint_ref, str) and endpoint_ref.startswith("ep_optillm_proxy"))
                ):
                    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-&|_")
                    if any(ch not in allowed for ch in value):
                        error(
                            errors,
                            lineno,
                            f"selector.{key}",
                            "must use lowercase letters, digits, dashes, and optillm separators (&, |) only",
                        )
                    continue
                if any(ch for ch in value if not (ch.islower() or ch.isdigit() or ch == "-")):
                    error(
                        errors,
                        lineno,
                        f"selector.{key}",
                        "must be lowercase letters, digits, or dashes only",
                    )

    notes = row.get("notes")
    if "notes" in row and (notes is None or not isinstance(notes, str)):
        error(errors, lineno, "notes", "must be a string if provided")

    return {
        "handle": handle,
        "kind": kind,
        "invoke": invoke,
        "endpoint_ref": endpoint_ref,
        "selector": selector,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate gateway handles registry JSONL.")
    parser.add_argument(
        "path",
        nargs="?",
        default="layer-gateway/registry/handles.jsonl",
        help="Path to handles.jsonl",
    )
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    errors = []
    handles = {}
    triplets = {}

    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                error(errors, lineno, "row", f"invalid JSON: {exc}")
                continue

            parsed = validate_row(row, lineno, errors)
            if not parsed:
                continue

            handle = parsed["handle"]
            if handle in handles:
                error(
                    errors,
                    lineno,
                    "handle",
                    f"duplicate handle; first seen on line {handles[handle]}",
                )
            else:
                handles[handle] = lineno

            selector_key = canonical_selector(parsed["selector"])
            triplet = (parsed["kind"], parsed["endpoint_ref"], selector_key)
            if triplet in triplets:
                error(
                    errors,
                    lineno,
                    "selector",
                    "duplicate (kind, endpoint_ref, selector); "
                    f"first seen on line {triplets[triplet]}",
                )
            else:
                triplets[triplet] = lineno

    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        return 1

    print(f"ok: {path} ({len(handles)} handles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
