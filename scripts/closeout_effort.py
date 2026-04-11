#!/usr/bin/env python3
"""Land a linked worktree locally and restore the primary baseline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from worktree_effort import (
    IMPLEMENTATION_STAGES,
    build_preflight_payload,
    gather_state,
    get_current_branch,
    get_repo_root,
    is_primary_worktree,
    paths_overlap,
    run_git,
)


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def ensure_clean_primary(repo_root: Path) -> None:
    if not is_primary_worktree(repo_root):
        raise SystemExit("closeout_effort.py must be run from the primary worktree")
    state = gather_state(repo_root)
    if not state["primary_worktree_baseline_ok"]:
        raise SystemExit("primary worktree must be a clean baseline before closeout")
    if get_current_branch(repo_root) != "master":
        raise SystemExit("primary worktree must be on master before closeout")


def worktree_info(repo_root: Path, target_path: Path) -> dict[str, object]:
    state = gather_state(repo_root)
    for item in state["active_worktrees"]:
        if item["path"] == str(target_path):
            return item
    raise SystemExit(f"target worktree is not part of this repo: {target_path}")


def branch_divergence(repo_root: Path, branch: str) -> tuple[int, int]:
    left, right = run_git(repo_root, "rev-list", "--left-right", "--count", f"master...{branch}").split()
    return (int(left), int(right))


def stage_scoped_changes(target_path: Path, scope_paths: list[str]) -> None:
    cmd = ["git", "-C", str(target_path), "add", "-A", "--", *scope_paths]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "failed to stage scoped changes")


def commit_all_staged(target_path: Path, message: str) -> str:
    commit = run(["git", "commit", "-m", message], target_path)
    if commit.returncode != 0:
        raise SystemExit(commit.stderr.strip() or commit.stdout.strip() or "failed to commit closeout changes")
    return run_git(target_path, "rev-parse", "HEAD")


def run_repo_audits(target_path: Path) -> tuple[bool, bool]:
    repo_hygiene = run([sys.executable, "scripts/repo_hygiene_audit.py", "--scope", "all", "--json"], target_path)
    if repo_hygiene.returncode != 0:
        raise SystemExit(repo_hygiene.stderr.strip() or repo_hygiene.stdout.strip() or "repo hygiene audit failed")
    repo_hygiene_ok = bool(json.loads(repo_hygiene.stdout)["overall_ok"])
    sync = run([sys.executable, "scripts/control_plane_sync_audit.py", "--json"], target_path)
    if sync.returncode != 0:
        raise SystemExit(sync.stderr.strip() or sync.stdout.strip() or "control-plane sync audit failed")
    sync_ok = bool(json.loads(sync.stdout)["overall_ok"])
    if not repo_hygiene_ok:
        raise SystemExit("repo hygiene audit reported overall_ok=false")
    if not sync_ok:
        raise SystemExit("control-plane sync audit reported overall_ok=false")
    return (repo_hygiene_ok, sync_ok)


def close_metadata_if_present(target_path: Path) -> bool:
    result = run([sys.executable, "scripts/worktree_effort.py", "close", "--json"], target_path)
    return result.returncode == 0


def remove_worktree_and_branch(repo_root: Path, target_path: Path, branch: str) -> tuple[bool, bool]:
    remove = run(["git", "worktree", "remove", "--force", str(target_path)], repo_root)
    if remove.returncode != 0:
        raise SystemExit(remove.stderr.strip() or remove.stdout.strip() or "failed to remove target worktree")
    prune = run(["git", "worktree", "prune"], repo_root)
    if prune.returncode != 0:
        raise SystemExit(prune.stderr.strip() or prune.stdout.strip() or "failed to prune worktrees")
    delete = run(["git", "branch", "-D", branch], repo_root)
    if delete.returncode != 0:
        raise SystemExit(delete.stderr.strip() or delete.stdout.strip() or "failed to delete target branch")
    return (True, True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--message")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = get_repo_root(Path.cwd())
    ensure_clean_primary(repo_root)
    target_path = Path(args.worktree).resolve()
    if target_path == repo_root:
        raise SystemExit("target worktree must not be the primary worktree")
    target = worktree_info(repo_root, target_path)
    branch = str(target["branch"])
    dirty_before = bool(target["dirty_paths"])
    target_effort = target["effort"] if isinstance(target["effort"], dict) else None
    commit_sha = None
    if dirty_before:
        if not target_effort or str(target_effort.get("stage")) not in IMPLEMENTATION_STAGES:
            raise SystemExit("dirty target worktree must have active build/verify metadata before closeout")
        preflight = build_preflight_payload(target_path, str(target_effort["stage"]))
        if not preflight["overall_ok"]:
            raise SystemExit("target worktree failed preflight and cannot be closed out")
        scope_paths = [str(item) for item in target_effort.get("scope_paths", [])]
        stage_scoped_changes(target_path, scope_paths)
        commit_sha = commit_all_staged(target_path, args.message or f"{target_effort['effort_id']}: closeout")
    behind_master_count, ahead_of_master_count = branch_divergence(repo_root, branch)
    if ahead_of_master_count == 0:
        raise SystemExit("nothing to close out")
    if behind_master_count != 0:
        raise SystemExit("target branch is not fast-forwardable from master; realign it manually before closeout")
    repo_hygiene_ok, sync_ok = run_repo_audits(target_path)
    merge = run(["git", "merge", "--ff-only", branch], repo_root)
    if merge.returncode != 0:
        raise SystemExit(merge.stderr.strip() or merge.stdout.strip() or "failed to fast-forward merge target branch")
    merged_sha = run_git(repo_root, "rev-parse", "HEAD")
    metadata_closed = close_metadata_if_present(target_path)
    worktree_removed, branch_deleted = remove_worktree_and_branch(repo_root, target_path, branch)
    final_state = gather_state(repo_root)
    final_ok = not final_state["overlaps"] and not final_state["dirty_missing_effort_metadata"] and not final_state["baseline_issues"]
    payload = {
        "target_worktree": str(target_path),
        "target_branch": branch,
        "target_effort_id": target_effort.get("effort_id") if target_effort else None,
        "dirty_before_closeout": dirty_before,
        "commit_created": bool(commit_sha),
        "commit_sha": commit_sha,
        "repo_hygiene_ok": repo_hygiene_ok,
        "control_plane_sync_ok": sync_ok,
        "merged_to_master": True,
        "merged_sha": merged_sha,
        "metadata_closed": metadata_closed,
        "worktree_removed": worktree_removed,
        "branch_deleted": branch_deleted,
        "overall_ok": final_ok,
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
