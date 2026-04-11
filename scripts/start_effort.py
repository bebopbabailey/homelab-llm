#!/usr/bin/env python3
"""Create a linked worktree and register a scoped effort from the clean primary baseline."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path, PurePosixPath

from service_registry import resolve_service_path
from worktree_effort import IMPLEMENTATION_STAGES, gather_state


BROAD_PARALLEL_PATHS = {
    "docs",
    "services",
    "experiments",
    "layer-gateway",
    "layer-inference",
    "layer-interface",
    "layer-tools",
    "layer-data",
}


def run_git(repo_path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def normalize_scope_path(value: str) -> str:
    text = value.strip().replace("\\", "/")
    if not text:
        raise ValueError("scope path may not be empty")
    path = PurePosixPath(text)
    if path.is_absolute():
        raise ValueError(f"scope path must be repo-relative: {value}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"scope path must not contain '.' or '..': {value}")
    return path.as_posix()


def paths_overlap(a: str, b: str) -> bool:
    left = PurePosixPath(a)
    right = PurePosixPath(b)
    return left == right or left in right.parents or right in left.parents


def sanitize_label(value: str) -> str:
    lowered = value.strip().lower()
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in lowered)
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts) or "effort"


def get_repo_root(repo_path: Path) -> Path:
    return Path(run_git(repo_path, "rev-parse", "--show-toplevel"))


def get_git_dir(repo_path: Path) -> Path:
    return Path(run_git(repo_path, "rev-parse", "--absolute-git-dir"))


def get_git_common_dir(repo_path: Path) -> Path:
    return Path(run_git(repo_path, "rev-parse", "--path-format=absolute", "--git-common-dir"))


def get_current_branch(repo_path: Path) -> str:
    branch = run_git(repo_path, "branch", "--show-current")
    return branch or "(detached)"


def is_primary_worktree(repo_root: Path) -> bool:
    return get_git_dir(repo_root) == get_git_common_dir(repo_root)


def collect_dirty_paths(repo_root: Path) -> list[str]:
    commands = [
        ("diff", "--name-only", "-z"),
        ("diff", "--cached", "--name-only", "-z"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ]
    dirty: set[str] = set()
    for args in commands:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        dirty.update(item for item in result.stdout.split("\0") if item)
    return sorted(dirty)


def effort_file_path(git_dir: Path) -> Path:
    return git_dir / "codex-effort.json"


def ensure_primary_on_master_and_clean(repo_root: Path) -> None:
    if not is_primary_worktree(repo_root):
        raise SystemExit("start_effort.py must be run from the primary worktree")
    if get_current_branch(repo_root) != "master":
        raise SystemExit("primary worktree must be on master before starting a linked effort")
    dirty_paths = collect_dirty_paths(repo_root)
    if dirty_paths:
        raise SystemExit("primary worktree must be clean before starting a linked effort")


def ensure_no_local_effort_metadata(repo_root: Path) -> None:
    effort_file = effort_file_path(get_git_dir(repo_root))
    if effort_file.exists():
        raise SystemExit("primary worktree must not have local effort metadata before starting a linked effort")


def branch_exists(repo_root: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def create_worktree(repo_root: Path, base_ref: str, branch: str, worktree_path: Path) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), "worktree", "add", "-b", branch, str(worktree_path), base_ref],
        check=True,
        capture_output=True,
        text=True,
    )
def failure_payload(message: str, **extra: object) -> dict[str, object]:
    payload = {
        "overall_ok": False,
        "message": message,
    }
    payload.update(extra)
    return payload


def print_payload(payload: dict[str, object], as_json: bool) -> None:
    print(json.dumps(payload, indent=2))


def cleanup_created_lane(repo_root: Path, branch: str, worktree_path: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if worktree_path.exists():
        result = subprocess.run(
            ["git", "-C", str(repo_root), "worktree", "remove", "--force", str(worktree_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            errors.append(result.stderr.strip() or result.stdout.strip() or "failed to remove created worktree")
    result = subprocess.run(
        ["git", "-C", str(repo_root), "branch", "-D", branch],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        if "not found" not in stderr and "branch named" not in stderr:
            errors.append(stderr or "failed to delete created branch")
    return (not errors, errors)


def find_prospective_overlaps(repo_root: Path, scope_paths: list[str]) -> list[dict[str, object]]:
    state = gather_state(repo_root)
    active_implementations = [
        item
        for item in state["active_worktrees"]
        if isinstance(item.get("effort"), dict) and str(item["effort"].get("stage")) in IMPLEMENTATION_STAGES
    ]
    overlaps = []
    for item in active_implementations:
        other_scopes = [str(scope) for scope in item["effort"].get("scope_paths", [])]
        matched = sorted(
            {
                f"{left} <-> {right}"
                for left in scope_paths
                for right in other_scopes
                if paths_overlap(left, right)
            }
        )
        if matched:
            overlaps.append({"path": item["path"], "effort_id": item["effort"].get("effort_id"), "overlaps": matched})
    return overlaps


def broad_parallel_issues(repo_root: Path, scope_paths: list[str]) -> list[str]:
    state = gather_state(repo_root)
    if int(state["active_implementation_effort_count"]) == 0:
        return []
    return sorted(path for path in scope_paths if path in BROAD_PARALLEL_PATHS)


def run_local_script(worktree_path: Path, script_name: str, *args: str) -> dict[str, object]:
    script = worktree_path / "scripts" / script_name
    result = subprocess.run(
        ["python3", str(script), *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=worktree_path,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or f"{script_name} failed")
    return json.loads(result.stdout)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, dest="effort_id")
    parser.add_argument("--scope", action="append", default=[])
    parser.add_argument("--service", action="append", default=[])
    parser.add_argument("--base", default="master")
    parser.add_argument("--branch")
    parser.add_argument("--path")
    parser.add_argument("--stage", choices=("build", "verify"), default="build")
    parser.add_argument("--owner", default="codex")
    parser.add_argument("--notes")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = get_repo_root(Path.cwd())
    ensure_primary_on_master_and_clean(repo_root)
    ensure_no_local_effort_metadata(repo_root)

    effort_label = sanitize_label(args.effort_id)
    service_ids = sorted({item.strip() for item in args.service if item.strip()})
    if not args.scope and not service_ids:
        raise SystemExit("start_effort.py requires at least one --scope or --service")
    resolved_service_scopes = [resolve_service_path(repo_root, service_id) for service_id in service_ids]
    scope_paths = sorted({normalize_scope_path(item) for item in [*args.scope, *resolved_service_scopes]})
    branch = args.branch or f"codex/{effort_label}"
    worktree_path = Path(args.path).resolve() if args.path else repo_root.parent / f"{repo_root.name}-{effort_label}"

    if branch_exists(repo_root, branch):
        raise SystemExit(f"target branch already exists: {branch}")
    if worktree_path.exists():
        raise SystemExit(f"target worktree path already exists: {worktree_path}")
    state = gather_state(repo_root)
    if state["dirty_missing_effort_metadata"]:
        payload = failure_payload(
            "another dirty worktree has no active effort metadata",
            failure_stage="precheck",
            blocking_issues=["another dirty worktree has no active effort metadata"],
            cleanup_attempted=False,
            cleanup_ok=True,
            cleanup_errors=[],
        )
        print_payload(payload, args.json)
        return 1
    overlap_issues = find_prospective_overlaps(repo_root, scope_paths)
    if overlap_issues:
        payload = failure_payload(
            "another active worktree has overlapping scope_paths",
            failure_stage="precheck",
            blocking_issues=["another active worktree has overlapping scope_paths"],
            overlaps=overlap_issues,
            cleanup_attempted=False,
            cleanup_ok=True,
            cleanup_errors=[],
        )
        print_payload(payload, args.json)
        return 1
    broad_issues = broad_parallel_issues(repo_root, scope_paths)
    if broad_issues:
        payload = failure_payload(
            "broad parallel docs/layer scopes are not allowed while another implementation effort is active",
            failure_stage="precheck",
            blocking_issues=["broad parallel docs/layer scopes are not allowed while another implementation effort is active"],
            broad_parallel_scope_paths=broad_issues,
            cleanup_attempted=False,
            cleanup_ok=True,
            cleanup_errors=[],
        )
        print_payload(payload, args.json)
        return 1

    created = False
    try:
        create_worktree(repo_root, args.base, branch, worktree_path)
        created = True

        register_args = [
            "register",
            "--effort-id",
            args.effort_id,
            "--stage",
            args.stage,
            "--owner",
            args.owner,
            "--json",
        ]
        for scope in scope_paths:
            register_args.extend(["--scope", scope])
        if args.notes:
            register_args.extend(["--notes", args.notes])
        run_local_script(worktree_path, "worktree_effort.py", *register_args)
        preflight_payload = run_local_script(
            worktree_path,
            "worktree_effort.py",
            "preflight",
            "--stage",
            args.stage,
            "--json",
        )
    except (subprocess.CalledProcessError, SystemExit) as error:
        cleanup_ok, cleanup_errors = cleanup_created_lane(repo_root, branch, worktree_path) if created else (True, [])
        payload = failure_payload(
            str(error),
            failure_stage="post-create" if created else "create-worktree",
            cleanup_attempted=created,
            cleanup_ok=cleanup_ok,
            cleanup_errors=cleanup_errors,
            blocking_issues=[str(error)],
        )
        print_payload(payload, args.json)
        return 1

    payload = {
        "primary_worktree": str(repo_root),
        "worktree_path": str(worktree_path),
        "branch": branch,
        "base_ref": args.base,
        "stage": args.stage,
        "service_ids": service_ids,
        "scope_paths": scope_paths,
        "register_ok": True,
        "preflight_ok": bool(preflight_payload.get("overall_ok")),
        "overall_ok": bool(preflight_payload.get("overall_ok")),
    }
    print_payload(payload, args.json)
    return 0 if payload["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
