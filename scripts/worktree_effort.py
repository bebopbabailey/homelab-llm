#!/usr/bin/env python3
"""Manage local per-worktree effort metadata for concurrent implementation safety."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


IMPLEMENTATION_STAGES = {"build", "verify"}
ALL_STAGES = ("discover", "design", "build", "verify", "parked")
ALL_STATUSES = {"active", "closed"}


def run_git(repo_path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_repo_root(repo_path: Path) -> Path:
    return Path(run_git(repo_path, "rev-parse", "--show-toplevel"))


def get_git_dir(repo_path: Path) -> Path:
    return Path(run_git(repo_path, "rev-parse", "--absolute-git-dir"))


def get_git_common_dir(repo_path: Path) -> Path:
    return Path(run_git(repo_path, "rev-parse", "--path-format=absolute", "--git-common-dir"))


def get_current_branch(repo_path: Path) -> str:
    branch = run_git(repo_path, "branch", "--show-current")
    return branch or "(detached)"


def get_branch_divergence(repo_path: Path, branch: str, base_ref: str = "master") -> tuple[int, int]:
    if branch == "(detached)":
        return (0, 0)
    result = subprocess.run(
        ["git", "-C", str(repo_path), "rev-list", "--left-right", "--count", f"{base_ref}...{branch}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return (0, 0)
    left, right = result.stdout.strip().split()
    return (int(left), int(right))


def sanitize_label(value: str) -> str:
    lowered = value.strip().lower()
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in lowered)
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts) or "worktree"


def get_worktree_label(repo_path: Path) -> str:
    return sanitize_label(repo_path.resolve().name)


def make_parked_effort_id(repo_path: Path) -> str:
    return f"parked:{get_worktree_label(repo_path)}"


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


def normalize_repo_path(path: str) -> str:
    return normalize_scope_path(path)


def paths_overlap(a: str, b: str) -> bool:
    left = PurePosixPath(a)
    right = PurePosixPath(b)
    return left == right or left in right.parents or right in left.parents


def effort_file_path(git_dir: Path) -> Path:
    return git_dir / "codex-effort.json"


def read_effort_file(git_dir: Path) -> dict[str, object] | None:
    path = effort_file_path(git_dir)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"effort file must contain a JSON object: {path}")
    status = str(data.get("status", ""))
    stage = str(data.get("stage", ""))
    if status not in ALL_STATUSES:
        raise ValueError(f"invalid effort status in {path}: {status}")
    if stage not in ALL_STAGES:
        raise ValueError(f"invalid effort stage in {path}: {stage}")
    scope_paths = data.get("scope_paths", [])
    if not isinstance(scope_paths, list):
        raise ValueError(f"scope_paths must be a list in {path}")
    data["scope_paths"] = [normalize_scope_path(str(item)) for item in scope_paths]
    return data


def write_effort_file(git_dir: Path, payload: dict[str, object]) -> Path:
    path = effort_file_path(git_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def parse_nul_list(text: str) -> list[str]:
    return [item for item in text.split("\0") if item]


def collect_dirty_paths(worktree_path: Path) -> list[str]:
    dirty: set[str] = set()
    commands = [
        ("diff", "--name-only", "-z"),
        ("diff", "--cached", "--name-only", "-z"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ]
    for args in commands:
        result = subprocess.run(
            ["git", "-C", str(worktree_path), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        for item in parse_nul_list(result.stdout):
            dirty.add(normalize_repo_path(item))
    return sorted(dirty)


def parse_worktree_list(repo_root: Path) -> list[dict[str, object]]:
    output = run_git(repo_root, "worktree", "list", "--porcelain")
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in output.splitlines():
        if line.startswith("worktree "):
            if current:
                entries.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif current is not None and " " in line:
            key, value = line.split(" ", 1)
            current[key] = value
        elif current is not None:
            current[line] = True
    if current:
        entries.append(current)
    return entries


def load_worktree_info(repo_root: Path) -> list[dict[str, object]]:
    infos: list[dict[str, object]] = []
    for entry in parse_worktree_list(repo_root):
        worktree_path = Path(str(entry["path"]))
        git_dir = get_git_dir(worktree_path)
        branch = get_current_branch(worktree_path)
        behind_master_count, ahead_of_master_count = get_branch_divergence(worktree_path, branch)
        effort = read_effort_file(git_dir)
        infos.append(
            {
                "path": str(worktree_path),
                "branch": branch,
                "git_dir": str(git_dir),
                "effort": effort,
                "dirty_paths": collect_dirty_paths(worktree_path),
                "behind_master_count": behind_master_count,
                "ahead_of_master_count": ahead_of_master_count,
            }
        )
    return infos


def get_primary_worktree_info(repo_root: Path, worktrees: list[dict[str, object]]) -> dict[str, object]:
    common_git_dir = str(get_git_common_dir(repo_root))
    for worktree in worktrees:
        if worktree["git_dir"] == common_git_dir:
            return worktree
    raise RuntimeError(f"could not locate primary worktree for common git dir {common_git_dir}")


def is_primary_worktree(repo_root: Path) -> bool:
    return get_git_dir(repo_root) == get_git_common_dir(repo_root)


def find_scope_overlaps(current_effort: dict[str, object] | None, current_path: str, worktrees: list[dict[str, object]]) -> list[dict[str, object]]:
    if not current_effort or current_effort.get("status") != "active":
        return []
    current_scopes = [str(item) for item in current_effort.get("scope_paths", [])]
    overlaps: list[dict[str, object]] = []
    for worktree in worktrees:
        if worktree["path"] == current_path:
            continue
        other_effort = worktree["effort"]
        if not isinstance(other_effort, dict) or other_effort.get("status") != "active":
            continue
        other_scopes = [str(item) for item in other_effort.get("scope_paths", [])]
        matched = sorted(
            {
                f"{left} <-> {right}"
                for left in current_scopes
                for right in other_scopes
                if paths_overlap(left, right)
            }
        )
        if matched:
            overlaps.append(
                {
                    "path": worktree["path"],
                    "effort_id": other_effort.get("effort_id"),
                    "overlaps": matched,
                }
            )
    return overlaps


def out_of_scope_dirty_paths(dirty_paths: list[str], scope_paths: list[str]) -> list[str]:
    if not scope_paths:
        return dirty_paths
    return sorted(path for path in dirty_paths if not any(paths_overlap(path, scope) for scope in scope_paths))


def gather_state(repo_root: Path) -> dict[str, object]:
    current_git_dir = get_git_dir(repo_root)
    current_path = str(repo_root)
    worktrees = load_worktree_info(repo_root)
    current_worktree = next(item for item in worktrees if item["path"] == current_path)
    primary_worktree = get_primary_worktree_info(repo_root, worktrees)
    current_effort = current_worktree["effort"]
    scope_paths = [str(item) for item in current_effort.get("scope_paths", [])] if isinstance(current_effort, dict) else []
    overlaps = find_scope_overlaps(current_effort, current_path, worktrees)
    missing_effort_metadata = sorted(
        item["path"]
        for item in worktrees
        if not isinstance(item["effort"], dict) or item["effort"].get("status") != "active"
    )
    dirty_missing_metadata = sorted(
        item["path"]
        for item in worktrees
        if item["dirty_paths"] and (not isinstance(item["effort"], dict) or item["effort"].get("status") != "active")
    )
    active_efforts = [
        item
        for item in worktrees
        if isinstance(item["effort"], dict) and item["effort"].get("status") == "active"
    ]
    active_implementation_efforts = [
        item
        for item in active_efforts
        if str(item["effort"].get("stage")) in IMPLEMENTATION_STAGES
    ]
    parked_worktrees = sorted(
        item["path"]
        for item in active_efforts
        if str(item["effort"].get("stage")) == "parked"
    )
    duplicate_effort_ids = sorted(
        {
            str(item["effort"].get("effort_id"))
            for item in active_efforts
            if item["effort"].get("effort_id")
            and sum(1 for other in active_efforts if other["effort"].get("effort_id") == item["effort"].get("effort_id")) > 1
        }
    )
    current_out_of_scope_dirty = out_of_scope_dirty_paths(current_worktree["dirty_paths"], scope_paths)
    baseline_issues: list[str] = []
    primary_effort = primary_worktree["effort"]
    if str(primary_worktree["branch"]) != "master":
        baseline_issues.append("primary worktree is not on master")
    if primary_worktree["dirty_paths"]:
        baseline_issues.append("primary worktree is dirty")
    if isinstance(primary_effort, dict) and str(primary_effort.get("stage")) == "parked":
        baseline_issues.append("primary worktree is parked")
    if isinstance(primary_effort, dict) and str(primary_effort.get("stage")) in IMPLEMENTATION_STAGES:
        baseline_issues.append("primary worktree has active implementation effort")
    closeout_candidates = [
        {
            "path": str(item["path"]),
            "branch": str(item["branch"]),
            "ahead_of_master_count": int(item["ahead_of_master_count"]),
        }
        for item in sorted(worktrees, key=lambda item: str(item["path"]))
        if item["path"] != current_path
        and not item["dirty_paths"]
        and int(item["ahead_of_master_count"]) > 0
    ]
    stale_active_efforts = [
        {
            "path": str(item["path"]),
            "branch": str(item["branch"]),
            "effort_id": str(item["effort"].get("effort_id")),
        }
        for item in sorted(active_implementation_efforts, key=lambda item: str(item["path"]))
        if not item["dirty_paths"] and int(item["ahead_of_master_count"]) == 0
    ]
    return {
        "current_worktree": current_path,
        "current_branch": get_current_branch(repo_root),
        "current_git_dir": str(current_git_dir),
        "primary_worktree_path": str(primary_worktree["path"]),
        "primary_worktree_branch": str(primary_worktree["branch"]),
        "is_primary_worktree": current_worktree["path"] == primary_worktree["path"],
        "current_effort": current_effort,
        "active_worktrees": worktrees,
        "active_effort_count": len(active_efforts),
        "active_implementation_effort_count": len(active_implementation_efforts),
        "parked_worktrees": parked_worktrees,
        "overlaps": overlaps,
        "missing_effort_metadata": missing_effort_metadata,
        "dirty_missing_effort_metadata": dirty_missing_metadata,
        "duplicate_effort_ids": duplicate_effort_ids,
        "out_of_scope_dirty_paths": current_out_of_scope_dirty,
        "closeout_candidates": closeout_candidates,
        "stale_active_efforts": stale_active_efforts,
        "baseline_issues": baseline_issues,
        "primary_worktree_baseline_ok": not baseline_issues,
    }


def build_preflight_payload(repo_root: Path, stage: str) -> dict[str, object]:
    state = gather_state(repo_root)
    warnings: list[str] = []
    blocking_issues: list[str] = []
    current_effort = state["current_effort"]

    if stage in IMPLEMENTATION_STAGES:
        if bool(state["is_primary_worktree"]):
            blocking_issues.append("primary worktree is baseline-only; start or move this effort to a linked worktree")
        if not isinstance(current_effort, dict):
            blocking_issues.append("no active local effort metadata registered for this worktree")
        else:
            if current_effort.get("status") != "active":
                blocking_issues.append("local effort metadata is not active")
            current_stage = str(current_effort.get("stage"))
            if current_stage == "parked":
                blocking_issues.append("current worktree is parked; register a build or verify effort before mutating")
            elif current_stage not in IMPLEMENTATION_STAGES:
                blocking_issues.append("local effort stage is not build/verify compatible")
            if current_stage in IMPLEMENTATION_STAGES and not current_effort.get("scope_paths"):
                blocking_issues.append("local effort metadata has no scope_paths")
        if state["out_of_scope_dirty_paths"]:
            blocking_issues.append("current worktree has dirty paths outside the registered scope")
        if state["overlaps"]:
            blocking_issues.append("another active worktree has overlapping scope_paths")
        if state["duplicate_effort_ids"]:
            blocking_issues.append("duplicate active effort_id detected across worktrees")
        if state["dirty_missing_effort_metadata"]:
            blocking_issues.append("another dirty worktree has no active effort metadata")
        if state["current_branch"] == "master" and state["active_implementation_effort_count"] > 1:
            blocking_issues.append("master must not host more than one active implementation effort")
        current_dirty = next(item for item in state["active_worktrees"] if item["path"] == state["current_worktree"])["dirty_paths"]
        if current_dirty and not isinstance(current_effort, dict):
            blocking_issues.append("dirty worktree has no registered effort")
    else:
        if not isinstance(current_effort, dict):
            warnings.append("no local effort metadata registered for this worktree")
        if state["dirty_missing_effort_metadata"]:
            warnings.append("another dirty worktree has no active effort metadata")
        if state["overlaps"]:
            warnings.append("active overlapping scopes exist across worktrees")

    state["requested_stage"] = stage
    state["warnings"] = warnings
    state["blocking_issues"] = blocking_issues
    state["overall_ok"] = not blocking_issues
    return state


def cmd_register(args: argparse.Namespace) -> int:
    repo_root = get_repo_root(Path.cwd())
    if args.stage in IMPLEMENTATION_STAGES and is_primary_worktree(repo_root):
        raise SystemExit("primary worktree is baseline-only; register build/verify efforts in a linked worktree")
    git_dir = get_git_dir(repo_root)
    scope_paths = sorted({normalize_scope_path(item) for item in args.scope})
    if args.stage in IMPLEMENTATION_STAGES and not scope_paths:
        raise SystemExit("Build/Verify registration requires at least one --scope path")
    existing = read_effort_file(git_dir)
    created_at = str(existing.get("created_at")) if isinstance(existing, dict) and existing.get("created_at") else now_utc()
    payload: dict[str, object] = {
        "effort_id": args.effort_id,
        "owner": args.owner,
        "stage": args.stage,
        "scope_paths": scope_paths,
        "status": "active",
        "created_at": created_at,
        "updated_at": now_utc(),
    }
    if args.notes:
        payload["notes"] = args.notes
    path = write_effort_file(git_dir, payload)
    result = {"effort_file": str(path), "effort": payload}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    return 0


def cmd_park(args: argparse.Namespace) -> int:
    repo_root = get_repo_root(Path.cwd())
    git_dir = get_git_dir(repo_root)
    existing = read_effort_file(git_dir)
    created_at = str(existing.get("created_at")) if isinstance(existing, dict) and existing.get("created_at") else now_utc()
    payload: dict[str, object] = {
        "effort_id": make_parked_effort_id(repo_root),
        "owner": args.owner,
        "stage": "parked",
        "scope_paths": [],
        "status": "active",
        "created_at": created_at,
        "updated_at": now_utc(),
    }
    if args.notes:
        payload["notes"] = args.notes
    path = write_effort_file(git_dir, payload)
    result = {"effort_file": str(path), "effort": payload}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    payload = gather_state(get_repo_root(Path.cwd()))
    payload["warnings"] = []
    payload["blocking_issues"] = []
    payload["overall_ok"] = (
        not payload["overlaps"]
        and not payload["dirty_missing_effort_metadata"]
        and not payload["baseline_issues"]
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    payload = build_preflight_payload(get_repo_root(Path.cwd()), args.stage)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    if args.stage in IMPLEMENTATION_STAGES and not payload["overall_ok"]:
        return 1
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    repo_root = get_repo_root(Path.cwd())
    git_dir = get_git_dir(repo_root)
    existing = read_effort_file(git_dir)
    if not isinstance(existing, dict):
        raise SystemExit("no local effort metadata exists for this worktree")
    path = effort_file_path(git_dir)
    path.unlink()
    result = {
        "removed": True,
        "removed_effort_file": str(path),
        "removed_effort": existing,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Register or update the local worktree effort")
    register.add_argument("--effort-id", required=True)
    register.add_argument("--stage", choices=ALL_STAGES, required=True)
    register.add_argument("--scope", action="append", default=[], help="Repo-relative file or directory scope path")
    register.add_argument("--owner", default="codex")
    register.add_argument("--notes")
    register.add_argument("--json", action="store_true")
    register.set_defaults(func=cmd_register)

    park = subparsers.add_parser("park", help="Mark the local worktree as parked context-only state")
    park.add_argument("--owner", default="codex")
    park.add_argument("--notes")
    park.add_argument("--json", action="store_true")
    park.set_defaults(func=cmd_park)

    status = subparsers.add_parser("status", help="Show current worktree-effort status")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    preflight = subparsers.add_parser("preflight", help="Check local concurrency safety before a stage")
    preflight.add_argument("--stage", choices=ALL_STAGES, required=True)
    preflight.add_argument("--json", action="store_true")
    preflight.set_defaults(func=cmd_preflight)

    close = subparsers.add_parser("close", help="Mark the local worktree effort closed")
    close.add_argument("--json", action="store_true")
    close.set_defaults(func=cmd_close)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
