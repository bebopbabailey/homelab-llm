#!/usr/bin/env python3
"""Create a linked worktree and register a scoped effort from the clean primary baseline."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path, PurePosixPath


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


def list_submodule_paths(repo_root: Path) -> list[str]:
    gitmodules = repo_root / ".gitmodules"
    if not gitmodules.is_file():
        return []
    result = subprocess.run(
        ["git", "-C", str(repo_root), "config", "-f", str(gitmodules), "--get-regexp", r"^submodule\..*\.path$"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in {0, 1}:
        raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)
    paths: list[str] = []
    for line in result.stdout.splitlines():
        _, value = line.split(" ", 1)
        paths.append(normalize_scope_path(value))
    return sorted(paths)


def submodules_overlapping_scope(submodule_paths: list[str], scope_paths: list[str]) -> list[str]:
    return sorted(
        path for path in submodule_paths if any(paths_overlap(path, scope) for scope in scope_paths)
    )


def create_worktree(repo_root: Path, base_ref: str, branch: str, worktree_path: Path) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), "worktree", "add", "-b", branch, str(worktree_path), base_ref],
        check=True,
        capture_output=True,
        text=True,
    )


def init_scoped_submodules(worktree_path: Path, submodule_paths: list[str]) -> None:
    if not submodule_paths:
        return
    subprocess.run(
        ["git", "-C", str(worktree_path), "-c", "protocol.file.allow=always", "submodule", "update", "--init", "--recursive", "--", *submodule_paths],
        check=True,
        capture_output=True,
        text=True,
    )


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
    parser.add_argument("--scope", action="append", required=True, default=[])
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
    scope_paths = sorted({normalize_scope_path(item) for item in args.scope})
    branch = args.branch or f"codex/{effort_label}"
    worktree_path = Path(args.path).resolve() if args.path else repo_root.parent / f"{repo_root.name}-{effort_label}"

    if branch_exists(repo_root, branch):
        raise SystemExit(f"target branch already exists: {branch}")
    if worktree_path.exists():
        raise SystemExit(f"target worktree path already exists: {worktree_path}")

    create_worktree(repo_root, args.base, branch, worktree_path)
    overlapping_submodules = submodules_overlapping_scope(list_submodule_paths(repo_root), scope_paths)
    init_scoped_submodules(worktree_path, overlapping_submodules)

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
    register_payload = run_local_script(worktree_path, "worktree_effort.py", *register_args)
    preflight_payload = run_local_script(
        worktree_path,
        "worktree_effort.py",
        "preflight",
        "--stage",
        args.stage,
        "--json",
    )

    payload = {
        "primary_worktree": str(repo_root),
        "worktree_path": str(worktree_path),
        "branch": branch,
        "base_ref": args.base,
        "stage": args.stage,
        "scope_paths": scope_paths,
        "initialized_submodules": overlapping_submodules,
        "register_ok": True,
        "preflight_ok": bool(preflight_payload.get("overall_ok")),
        "overall_ok": bool(preflight_payload.get("overall_ok")),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    return 0 if payload["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
