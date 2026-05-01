#!/usr/bin/env python3
"""Idempotent runtime patches for Open WebUI middleware and retrieval.

Why this exists:
- Open WebUI 0.8.7 can treat query-generation responses as dict-only and
  fallback to `queries = [response]` on parse errors.
- In practice this can leak JSON/reasoning blobs into search `q`, degrading
  retrieval quality.
- The local `chatgpt-5` lane is intended to stay text-only in Open WebUI, so
  any default terminal or terminal-tool re-entry must be stripped at the
  middleware layer on restart.
- The supported web-search path needs one narrow hygiene pass so obvious
  zero-overlap junk does not get fetched and embedded.

This script patches the installed Open WebUI files in-place and is safe to run
repeatedly (no-op when already patched).
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import shutil
import sys

QUERYGEN_PATCH_MARKER = (
    "querygen-hardening: avoid poisoned queries fallback; "
    "normalize generated search queries"
)
CHATGPT5_PATCH_MARKER = "chatgpt5-text-only-hardening: disable terminal re-entry"
RESULT_HYGIENE_PATCH_MARKER = (
    "web-search-result-hygiene: drop low-overlap junk before fetch; keep bounded low-confidence fallback"
)
LEGACY_RESULT_HYGIENE_PATCH_MARKER = (
    "web-search-result-hygiene: drop low-overlap junk before fetch"
)

QUERYGEN_ORIGINAL_BLOCK = """        response = res["choices"][0]["message"]["content"]

        try:
            bracket_start = response.find("{")
            bracket_end = response.rfind("}") + 1

            if bracket_start == -1 or bracket_end == -1:
                raise Exception("No JSON object found in the response")

            response = response[bracket_start:bracket_end]
            queries = json.loads(response)
            queries = queries.get("queries", [])
        except Exception as e:
            queries = [response]
"""

QUERYGEN_FIRST_PASS_BLOCK = """        response_obj = res
        if hasattr(response_obj, "body"):
            try:
                body = getattr(response_obj, "body")
                if isinstance(body, bytes):
                    body = body.decode("utf-8", errors="replace")
                response_obj = json.loads(body)
            except Exception:
                response_obj = {}

        response = ""
        if isinstance(response_obj, dict):
            choices = response_obj.get("choices")
            if isinstance(choices, list) and choices:
                first_choice = choices[0] if isinstance(choices[0], dict) else {}
                message = first_choice.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", "")
                    response = content if isinstance(content, str) else str(content or "")

        try:
            bracket_start = response.find("{")
            bracket_end = response.rfind("}") + 1

            if bracket_start == -1 or bracket_end <= bracket_start:
                raise ValueError("no_json_object")

            response = response[bracket_start:bracket_end]
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                parsed_queries = parsed.get("queries", [])
                if isinstance(parsed_queries, list):
                    queries = [q.strip() for q in parsed_queries if isinstance(q, str) and q.strip()]
        except Exception as e:
            log.debug("querygen_parse_fallback user_message=%r error=%s", user_message, e)
            queries = [user_message]

        if not queries:
            queries = [user_message]
        # querygen-hardening: avoid poisoned queries fallback
"""

QUERYGEN_HARDENED_BLOCK = """        response_obj = res
        if hasattr(response_obj, "body"):
            try:
                body = getattr(response_obj, "body")
                if isinstance(body, bytes):
                    body = body.decode("utf-8", errors="replace")
                response_obj = json.loads(body)
            except Exception:
                response_obj = {}

        response = ""
        if isinstance(response_obj, dict):
            choices = response_obj.get("choices")
            if isinstance(choices, list) and choices:
                first_choice = choices[0] if isinstance(choices[0], dict) else {}
                message = first_choice.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", "")
                    response = content if isinstance(content, str) else str(content or "")

        def _querygen_normalize_whitespace(value):
            return re.sub(r"\\s+", " ", str(value or "")).strip()

        def _querygen_compact_key(value):
            return re.sub(
                r"[^a-z0-9]+",
                " ",
                _querygen_normalize_whitespace(value).lower(),
            ).strip()

        def _querygen_move_leading_date_terms(value):
            month_tokens = {
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
                "august",
                "september",
                "october",
                "november",
                "december",
            }
            quarter_tokens = {"q1", "q2", "q3", "q4"}
            tokens = _querygen_normalize_whitespace(value).split(" ")
            leading = []
            index = 0

            while index < len(tokens):
                token = tokens[index].strip(",")
                lowered = token.lower()
                if (
                    lowered in month_tokens
                    or lowered in quarter_tokens
                    or re.fullmatch(r"\\d{4}", token)
                ):
                    leading.append(token)
                    index += 1
                    continue
                break

            if leading and index < len(tokens):
                tokens = tokens[index:] + leading

            return " ".join(token for token in tokens if token).strip()

        def _querygen_append_unique(values, candidate, limit):
            candidate = _querygen_normalize_whitespace(candidate)
            if not candidate:
                return

            candidate_key = _querygen_compact_key(candidate)
            if not candidate_key:
                return

            for existing in values:
                if _querygen_compact_key(existing) == candidate_key:
                    return

            if len(values) < limit:
                values.append(candidate)

        try:
            bracket_start = response.find("{")
            bracket_end = response.rfind("}") + 1

            if bracket_start == -1 or bracket_end <= bracket_start:
                raise ValueError("no_json_object")

            response = response[bracket_start:bracket_end]
            parsed = json.loads(response)
            parsed_queries = []
            if isinstance(parsed, dict):
                raw_parsed_queries = parsed.get("queries", [])
                if isinstance(raw_parsed_queries, list):
                    parsed_queries = raw_parsed_queries
        except Exception as e:
            log.debug("querygen_parse_fallback user_message=%r error=%s", user_message, e)
            parsed_queries = []

        raw_user_query = _querygen_normalize_whitespace(user_message)
        queries = []
        _querygen_append_unique(queries, raw_user_query, limit=3)

        for query in parsed_queries:
            if not isinstance(query, str):
                continue
            normalized_query = _querygen_move_leading_date_terms(query)
            _querygen_append_unique(queries, normalized_query, limit=3)

        user_token_set = set(_querygen_compact_key(user_message).split())
        topic_tail = _querygen_move_leading_date_terms(raw_user_query)

        community_signals = {
            "forum",
            "forums",
            "community",
            "communities",
            "reddit",
            "discussion",
            "discussions",
            "sentiment",
        }
        freshness_signals = {"today", "latest", "recent", "current", "news"}

        if topic_tail and user_token_set.intersection(community_signals):
            _querygen_append_unique(
                queries,
                f"community discussion {topic_tail}",
                limit=3,
            )

        if topic_tail and user_token_set.intersection(freshness_signals):
            _querygen_append_unique(
                queries,
                f"latest news {topic_tail}",
                limit=3,
            )

        if not queries:
            queries = [raw_user_query or user_message]
        # __PATCH_MARKER__
""".replace("__PATCH_MARKER__", QUERYGEN_PATCH_MARKER)

CHATGPT5_DEFAULT_TERMINAL_OLD = """def _default_chatgpt5_terminal_id(
    model_id: str,
    terminal_id,
    tool_ids,
    payload_tools,
    available_terminal_ids,
):
    if model_id != "chatgpt-5":
        return terminal_id
    if terminal_id or tool_ids or payload_tools:
        return terminal_id
    if "open-terminal" in (available_terminal_ids or []):
        return "open-terminal"
    return terminal_id
"""

CHATGPT5_DEFAULT_TERMINAL_NEW = """def _default_chatgpt5_terminal_id(
    model_id: str,
    terminal_id,
    tool_ids,
    payload_tools,
    available_terminal_ids,
):
    if model_id == "chatgpt-5":
        # __PATCH_MARKER__
        return None
    return terminal_id
""".replace("__PATCH_MARKER__", CHATGPT5_PATCH_MARKER)

CHATGPT5_TERMINAL_RESOLUTION_OLD = """        if terminal_id:
            try:
                terminal_tools = await get_terminal_tools(
                    request,
                    terminal_id,
                    user,
                    extra_params,
                )
"""

CHATGPT5_TERMINAL_RESOLUTION_NEW = """        if terminal_id and form_data["model"] != "chatgpt-5":
            try:
                terminal_tools = await get_terminal_tools(
                    request,
                    terminal_id,
                    user,
                    extra_params,
                )
"""

RESULT_HYGIENE_OLD = """        search_results = await asyncio.gather(*search_tasks)

        for result in search_results:
            if result:
                for item in result:
                    if item and item.link:
                        result_items.append(item)
                        urls.append(item.link)

        urls = list(dict.fromkeys(urls))
        log.debug(f"urls: {urls}")
"""

RESULT_HYGIENE_NEW = """        search_results = await asyncio.gather(*search_tasks)

        def _canonical_search_url(value):
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(value or "")
            if not parsed.scheme or not parsed.netloc:
                return value

            return urlunparse(
                (
                    parsed.scheme.lower(),
                    parsed.netloc.lower(),
                    parsed.path.rstrip("/"),
                    "",
                    "",
                    "",
                )
            )

        def _query_signal_tokens(values):
            stop_tokens = {
                "about",
                "after",
                "based",
                "community",
                "current",
                "discussion",
                "discussions",
                "forum",
                "forums",
                "from",
                "latest",
                "news",
                "opinion",
                "opinions",
                "people",
                "recent",
                "reddit",
                "saying",
                "sentiment",
                "today",
                "what",
                "with",
            }
            month_tokens = {
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
                "august",
                "september",
                "october",
                "november",
                "december",
            }
            tokens = set()

            for value in values:
                for token in re.findall(r"[a-z0-9]{2,}", (value or "").lower()):
                    if token in stop_tokens or token in month_tokens:
                        continue
                    if re.fullmatch(r"\\d{4}", token):
                        continue
                    if len(token) < 4:
                        continue
                    tokens.add(token)

            return tokens

        high_signal_tokens = _query_signal_tokens(form_data.queries)
        min_overlap = 1 if len(high_signal_tokens) <= 2 else 2
        candidates = []
        seen_urls = set()

        for result in search_results:
            if not result:
                continue
            for item in result:
                if not item or not item.link:
                    continue
                canonical_url = _canonical_search_url(item.link)
                if canonical_url in seen_urls:
                    continue
                seen_urls.add(canonical_url)

                overlap_count = 0
                if high_signal_tokens:
                    haystack = " ".join(
                        part for part in [item.title, item.snippet] if part
                    ).lower()
                    result_tokens = {
                        token
                        for token in re.findall(r"[a-z0-9]{2,}", haystack)
                        if len(token) >= 4 and not re.fullmatch(r"\\d{4}", token)
                    }
                    overlap_count = len(high_signal_tokens.intersection(result_tokens))

                candidates.append((overlap_count, item))

        if high_signal_tokens:
            strong_items = [
                item for overlap_count, item in candidates if overlap_count >= min_overlap
            ]
            weak_items = [item for overlap_count, item in candidates if overlap_count > 0]

            low_confidence_items = [item for _, item in candidates[:2]]

            if strong_items:
                result_items = strong_items
            elif weak_items:
                result_items = weak_items[:2]
            else:
                result_items = low_confidence_items
        else:
            result_items = [item for _, item in candidates]

        urls = [item.link for item in result_items]
        search_results = [result_items]
        log.debug(f"urls: {urls}")
        # __PATCH_MARKER__
""".replace("__PATCH_MARKER__", RESULT_HYGIENE_PATCH_MARKER)

PATCH_SPECS = {
    "middleware": [
        {
            "name": "querygen",
            "marker": QUERYGEN_PATCH_MARKER,
            "replacements": [
                (QUERYGEN_ORIGINAL_BLOCK, QUERYGEN_HARDENED_BLOCK),
                (QUERYGEN_FIRST_PASS_BLOCK, QUERYGEN_HARDENED_BLOCK),
            ],
        },
        {
            "name": "chatgpt5_text_only_default_terminal",
            "marker": CHATGPT5_PATCH_MARKER,
            "replacements": [
                (CHATGPT5_DEFAULT_TERMINAL_OLD, CHATGPT5_DEFAULT_TERMINAL_NEW)
            ],
        },
        {
            "name": "chatgpt5_text_only_terminal_resolution",
            "marker": CHATGPT5_PATCH_MARKER,
            "replacements": [
                (
                    CHATGPT5_TERMINAL_RESOLUTION_OLD,
                    CHATGPT5_TERMINAL_RESOLUTION_NEW,
                )
            ],
        },
    ],
    "retrieval": [
        {
            "name": "web_search_result_hygiene",
            "marker": RESULT_HYGIENE_PATCH_MARKER,
            "replacements": [
                (RESULT_HYGIENE_OLD, RESULT_HYGIENE_NEW),
                (
                    RESULT_HYGIENE_NEW.replace(
                        "            low_confidence_items = [item for _, item in candidates[:2]]\n\n"
                        "            if strong_items:\n"
                        "                result_items = strong_items\n"
                        "            elif weak_items:\n"
                        "                result_items = weak_items[:2]\n"
                        "            else:\n"
                        "                result_items = low_confidence_items\n",
                        "            if strong_items:\n"
                        "                result_items = strong_items\n"
                        "            elif len(high_signal_tokens) >= 4:\n"
                        "                result_items = []\n"
                        "            elif weak_items:\n"
                        "                result_items = weak_items\n"
                        "            else:\n"
                        "                result_items = [item for _, item in candidates]\n",
                    ),
                    RESULT_HYGIENE_NEW,
                ),
                (
                    RESULT_HYGIENE_NEW.replace(
                        RESULT_HYGIENE_PATCH_MARKER,
                        LEGACY_RESULT_HYGIENE_PATCH_MARKER,
                    ).replace(
                        "            low_confidence_items = [item for _, item in candidates[:2]]\n\n"
                        "            if strong_items:\n"
                        "                result_items = strong_items\n"
                        "            elif weak_items:\n"
                        "                result_items = weak_items[:2]\n"
                        "            else:\n"
                        "                result_items = low_confidence_items\n",
                        "            if strong_items:\n"
                        "                result_items = strong_items\n"
                        "            elif len(high_signal_tokens) >= 4:\n"
                        "                result_items = []\n"
                        "            elif weak_items:\n"
                        "                result_items = weak_items\n"
                        "            else:\n"
                        "                result_items = [item for _, item in candidates]\n",
                    ),
                    RESULT_HYGIENE_NEW,
                ),
            ],
        }
    ],
}


def infer_retrieval_target(middleware_target: Path) -> Path:
    package_root = middleware_target.parents[1]
    return package_root / "routers" / "retrieval.py"


def patch_text(content: str, patch_specs: list[dict[str, object]]) -> tuple[str, bool, dict[str, str]]:
    statuses: dict[str, str] = {}
    changed = False

    for patch in patch_specs:
        name = str(patch["name"])
        marker = str(patch["marker"])
        replacements = list(patch["replacements"])

        replaced = False
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                statuses[name] = "patched"
                changed = True
                replaced = True
                break

        if replaced:
            continue

        if marker in content:
            statuses[name] = "already_patched"
        else:
            statuses[name] = "pattern_not_found"

    return content, changed, statuses


def patch_target(target: Path, patch_specs: list[dict[str, object]]) -> tuple[bool, dict[str, str]]:
    content = target.read_text(encoding="utf-8")
    patched_content, changed, statuses = patch_text(content, patch_specs)
    if changed:
        target.write_text(patched_content, encoding="utf-8")
    return changed, statuses


def make_backup(target: Path, backup_dir: Path | None, label: str) -> Path:
    timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d%H%M%S")
    if backup_dir is None:
        backup_dir = target.parent
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{target.name}.bak.{label}.{timestamp}"
    shutil.copy2(target, backup)
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Patch Open WebUI middleware and retrieval hotfixes."
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Path to open_webui/utils/middleware.py",
    )
    parser.add_argument(
        "--retrieval-target",
        default="",
        help="Optional path to open_webui/routers/retrieval.py",
    )
    parser.add_argument("--backup-dir", default="", help="Optional backup directory")
    args = parser.parse_args()

    middleware_target = Path(args.target).resolve()
    if not middleware_target.exists():
        print(
            f"[openwebui_querygen_hotfix] target not found: {middleware_target}",
            file=sys.stderr,
        )
        return 2

    retrieval_target = (
        Path(args.retrieval_target).resolve()
        if args.retrieval_target
        else infer_retrieval_target(middleware_target)
    )
    if not retrieval_target.exists():
        print(
            f"[openwebui_querygen_hotfix] retrieval target not found: {retrieval_target}",
            file=sys.stderr,
        )
        return 2

    backup_dir = Path(args.backup_dir).resolve() if args.backup_dir else None
    middleware_backup = make_backup(middleware_target, backup_dir, "middleware")
    retrieval_backup = make_backup(retrieval_target, backup_dir, "retrieval")

    middleware_changed, middleware_statuses = patch_target(
        middleware_target, PATCH_SPECS["middleware"]
    )
    retrieval_changed, retrieval_statuses = patch_target(
        retrieval_target, PATCH_SPECS["retrieval"]
    )

    statuses = {**middleware_statuses, **retrieval_statuses}
    overall_ok = all(
        status in {"patched", "already_patched"} for status in statuses.values()
    )
    print(
        "[openwebui_querygen_hotfix] "
        f"status={','.join(f'{name}:{status}' for name, status in statuses.items())} "
        f"middleware_target={middleware_target} middleware_backup={middleware_backup} "
        f"retrieval_target={retrieval_target} retrieval_backup={retrieval_backup} "
        f"middleware_changed={middleware_changed} retrieval_changed={retrieval_changed}",
        file=sys.stdout,
    )
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
