#!/usr/bin/env python3
"""Audit whether submodule gitlink commits are locally present and remotely reachable."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from worktree_effort import get_repo_root, normalize_scope_path, paths_overlap, run_git


def list_submodules(repo_root: Path) -> list[dict[str, str]]:
    gitmodules = repo_root / ".gitmodules"
    if not gitmodules.is_file():
        return []
    result = subprocess.run(
        ["git", "-C", str(repo_root), "config", "-f", str(gitmodules), "--get-regexp", r"^submodule\..*\.(path|url)$"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in {0, 1}:
        raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)
    records: dict[str, dict[str, str]] = {}
    for line in result.stdout.splitlines():
        key, value = line.split(" ", 1)
        parts = key.split(".")
        name = parts[1]
        field = parts[2]
        records.setdefault(name, {})[field] = value.strip()
    submodules = []
    for record in records.values():
        if "path" in record and "url" in record:
            submodules.append({"path": normalize_scope_path(record["path"]), "url": record["url"]})
    return sorted(submodules, key=lambda item: item["path"])


def filter_submodules(submodules: list[dict[str, str]], scopes: list[str]) -> list[dict[str, str]]:
    if not scopes:
        return submodules
    return [item for item in submodules if any(paths_overlap(item["path"], scope) for scope in scopes)]


def gitlink_commit_from_ref(repo_root: Path, ref: str, rel_path: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-tree", ref, rel_path],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    fields = result.stdout.strip().split()
    if len(fields) < 3 or fields[1] != "commit":
        return None
    return fields[2]


def gitlink_commit_from_worktree(worktree: Path, rel_path: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(worktree), "ls-files", "--stage", "--", rel_path],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    fields = result.stdout.strip().split()
    if len(fields) < 2:
        return None
    return fields[1]


def resolve_gitdir(gitfile_path: Path) -> Path | None:
    if not gitfile_path.is_file():
        return None
    text = gitfile_path.read_text(encoding="utf-8").strip()
    prefix = "gitdir: "
    if not text.startswith(prefix):
        return None
    return (gitfile_path.parent / text[len(prefix):]).resolve()


def fallback_module_gitdir(repo_root: Path, rel_path: str) -> Path:
    return repo_root / ".git" / "modules" / Path(rel_path)


def local_gitdir_for_submodule(repo_root: Path, rel_path: str, worktree: Path | None) -> Path | None:
    if worktree is not None:
        resolved = resolve_gitdir(worktree / rel_path / ".git")
        if resolved is not None:
            return resolved
    fallback = fallback_module_gitdir(repo_root, rel_path)
    if fallback.exists():
        return fallback
    return None


def local_commit_present(git_dir: Path | None, commit: str) -> bool:
    if git_dir is None:
        return False
    result = subprocess.run(
        ["git", "-C", str(git_dir), "cat-file", "-e", f"{commit}^{{commit}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def remote_commit_reachable(remote_url: str, commit: str) -> tuple[bool, str | None]:
    with tempfile.TemporaryDirectory(prefix="submodule-pin-audit-") as tmpdir:
        bare_repo = Path(tmpdir) / "probe.git"
        init = subprocess.run(
            ["git", "init", "--bare", str(bare_repo)],
            check=False,
            capture_output=True,
            text=True,
        )
        if init.returncode != 0:
            return (False, init.stderr.strip() or init.stdout.strip() or "failed to initialize probe repo")
        fetch = subprocess.run(
            ["git", "-C", str(bare_repo), "fetch", "--depth=1", remote_url, commit],
            check=False,
            capture_output=True,
            text=True,
        )
        if fetch.returncode == 0:
            return (True, None)
        return (False, fetch.stderr.strip() or fetch.stdout.strip() or "remote fetch failed")


def audit_submodule(repo_root: Path, rel_path: str, remote_url: str, expected_commit: str, worktree: Path | None) -> dict[str, object]:
    git_dir = local_gitdir_for_submodule(repo_root, rel_path, worktree)
    local_present = local_commit_present(git_dir, expected_commit)
    remote_ok, remote_error = remote_commit_reachable(remote_url, expected_commit)
    issues: list[str] = []
    if not local_present:
        issues.append("expected commit is not present locally")
    if not remote_ok:
        issues.append("expected commit is not reachable from remote")
    if git_dir is None:
        issues.append("no local submodule object store found")
    payload = {
        "path": rel_path,
        "expected_commit": expected_commit,
        "remote_url": remote_url,
        "local_git_dir": str(git_dir) if git_dir else None,
        "local_commit_present": local_present,
        "remote_commit_reachable": remote_ok,
        "issues": issues,
    }
    if remote_error:
        payload["remote_error"] = remote_error
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref")
    parser.add_argument("--worktree")
    parser.add_argument("--scope", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if bool(args.ref) == bool(args.worktree):
        raise SystemExit("exactly one of --ref or --worktree is required")
    repo_root = get_repo_root(Path.cwd())
    scopes = sorted({normalize_scope_path(item) for item in args.scope})
    worktree = Path(args.worktree).resolve() if args.worktree else None
    submodules = filter_submodules(list_submodules(repo_root), scopes)
    failures: list[dict[str, object]] = []
    checked_paths: list[str] = []
    for item in submodules:
        rel_path = item["path"]
        expected_commit = (
            gitlink_commit_from_worktree(worktree, rel_path)
            if worktree is not None
            else gitlink_commit_from_ref(repo_root, str(args.ref), rel_path)
        )
        if not expected_commit:
            continue
        checked_paths.append(rel_path)
        payload = audit_submodule(repo_root, rel_path, item["url"], expected_commit, worktree)
        if payload["issues"]:
            failures.append(payload)
    result = {
        "checked_paths": checked_paths,
        "failures": failures,
        "overall_ok": not failures,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    if args.strict and failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
