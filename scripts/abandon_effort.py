#!/usr/bin/env python3
"""Abandon a linked worktree without losing append-only journal records."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from worktree_effort import gather_state, get_current_branch, get_repo_root, is_primary_worktree, run_git


JOURNAL_DIR = "docs/journal"
JOURNAL_ENTRY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[-a-z0-9]+\.md$")


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def ensure_clean_primary(repo_root: Path) -> None:
    if not is_primary_worktree(repo_root):
        raise SystemExit("abandon_effort.py must be run from the primary worktree")
    state = gather_state(repo_root)
    if not state["primary_worktree_baseline_ok"]:
        raise SystemExit("primary worktree must be a clean baseline before abandon")
    if get_current_branch(repo_root) != "master":
        raise SystemExit("primary worktree must be on master before abandon")


def worktree_info(repo_root: Path, target_path: Path) -> dict[str, object]:
    state = gather_state(repo_root)
    for item in state["active_worktrees"]:
        if item["path"] == str(target_path):
            return item
    raise SystemExit(f"target worktree is not part of this repo: {target_path}")


def is_journal_path(path: str) -> bool:
    return path == JOURNAL_DIR or path.startswith(f"{JOURNAL_DIR}/")


def is_journal_entry(path: str) -> bool:
    name = Path(path).name
    return path.startswith(f"{JOURNAL_DIR}/") and JOURNAL_ENTRY_RE.match(name) is not None


def master_has_path(repo_root: Path, path: str) -> bool:
    result = run(["git", "cat-file", "-e", f"master:{path}"], repo_root)
    return result.returncode == 0


def target_has_path(target_path: Path, path: str) -> bool:
    return (target_path / path).is_file()


def diff_name_status(repo_root: Path, branch: str) -> dict[str, str]:
    result = run(["git", "diff", "--name-status", f"master...{branch}", "--", JOURNAL_DIR], repo_root)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "failed to diff journal paths")
    statuses: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        if is_journal_path(path):
            statuses[path] = status
    return statuses


def dirty_journal_paths(target_path: Path) -> dict[str, str]:
    result = run(["git", "status", "--porcelain", "--", JOURNAL_DIR], target_path)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "failed to inspect target journal status")
    statuses: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2].strip() or "M"
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if is_journal_path(path):
            statuses[path] = status
    return statuses


def collect_journal_deltas(repo_root: Path, target_path: Path, branch: str) -> dict[str, list[str]]:
    statuses = diff_name_status(repo_root, branch)
    statuses.update(dirty_journal_paths(target_path))

    added_entries: list[str] = []
    modified_entries: list[str] = []
    deleted_entries: list[str] = []
    support_files: list[str] = []
    for path, status in sorted(statuses.items()):
        if not is_journal_entry(path):
            support_files.append(path)
            continue
        exists_on_master = master_has_path(repo_root, path)
        exists_on_target = target_has_path(target_path, path)
        if status.startswith("D") or (exists_on_master and not exists_on_target):
            deleted_entries.append(path)
        elif not exists_on_master and exists_on_target:
            added_entries.append(path)
        elif exists_on_master and exists_on_target:
            modified_entries.append(path)

    return {
        "added_entries": added_entries,
        "modified_entries": modified_entries,
        "deleted_entries": deleted_entries,
        "support_files": sorted(support_files),
        "all_paths": sorted(statuses),
    }


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


def target_diff(target_path: Path, path: str) -> str:
    result = run(["git", "diff", "--no-ext-diff", "--no-color", "master", "--", path], target_path)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or f"failed to capture diff for {path}")
    return result.stdout


def salvage_entry_path(repo_root: Path, requested_name: str | None) -> Path:
    name = requested_name
    if not name:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        name = f"{today}-abandoned-branch-journal-salvage.md"
    if "/" in name or not JOURNAL_ENTRY_RE.match(name):
        raise SystemExit("salvage entry name must match YYYY-MM-DD-<slug>.md")
    path = repo_root / JOURNAL_DIR / name
    if path.exists():
        raise SystemExit(f"salvage entry already exists: {JOURNAL_DIR}/{name}")
    return path


def write_modified_entry_salvage(
    repo_root: Path,
    target_path: Path,
    branch: str,
    modified_entries: list[str],
    requested_name: str | None,
) -> str | None:
    if not modified_entries:
        return None
    path = salvage_entry_path(repo_root, requested_name)
    title_date = path.name[:10]
    sections = [
        f"# {title_date} - Abandoned branch journal salvage",
        "",
        "## Source",
        f"- Branch: `{branch}`",
        f"- Worktree: `{target_path}`",
        "",
        "## Existing-entry corrections",
        "The abandoned branch modified existing append-only journal entries. The original entries were left unchanged; the attempted corrections are preserved here.",
        "",
    ]
    for entry in modified_entries:
        diff_text = target_diff(target_path, entry).rstrip()
        sections.extend([f"### `{entry}`", "", "```diff", diff_text, "```", ""])
    path.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    return f"{JOURNAL_DIR}/{path.name}"


def update_journal_index(repo_root: Path, entries: list[str]) -> None:
    index_path = repo_root / JOURNAL_DIR / "index.md"
    lines = index_path.read_text(encoding="utf-8").splitlines()
    existing_targets = {
        match.group(1)
        for line in lines
        if (match := re.search(r"\]\(([^)]+)\)", line))
    }
    new_names = sorted(
        {Path(entry).name for entry in entries if Path(entry).name not in existing_targets},
        reverse=True,
    )
    for name in new_names:
        link = f"- [{Path(name).stem}]({name})"
        inserted = False
        for index, line in enumerate(lines):
            match = re.search(r"\]\(([^)]+)\)", line)
            if match and match.group(1) < name:
                lines.insert(index, link)
                inserted = True
                break
        if not inserted:
            lines.append(link)
    index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def salvage_journal(
    repo_root: Path,
    target_path: Path,
    branch: str,
    deltas: dict[str, list[str]],
    message: str,
    salvage_entry: str | None,
) -> str | None:
    salvaged_entries: list[str] = []
    for entry in deltas["added_entries"]:
        source = target_path / entry
        destination = repo_root / entry
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        salvaged_entries.append(entry)
    correction_entry = write_modified_entry_salvage(
        repo_root,
        target_path,
        branch,
        deltas["modified_entries"],
        salvage_entry,
    )
    if correction_entry:
        salvaged_entries.append(correction_entry)
    if salvaged_entries:
        update_journal_index(repo_root, salvaged_entries)
        add = run(["git", "add", "--", *salvaged_entries, f"{JOURNAL_DIR}/index.md"], repo_root)
        if add.returncode != 0:
            raise SystemExit(add.stderr.strip() or add.stdout.strip() or "failed to stage salvaged journal records")
        commit = run(["git", "commit", "-m", message], repo_root)
        if commit.returncode != 0:
            raise SystemExit(commit.stderr.strip() or commit.stdout.strip() or "failed to commit salvaged journal records")
        return run_git(repo_root, "rev-parse", "HEAD")
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--salvage-journal", action="store_true")
    parser.add_argument("--salvage-entry")
    parser.add_argument("--message", default="journal: salvage abandoned experiment records")
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
    if branch == "(detached)":
        raise SystemExit("target worktree must be on a local branch")

    deltas = collect_journal_deltas(repo_root, target_path, branch)
    if deltas["all_paths"] and not args.salvage_journal:
        payload = {
            "target_worktree": str(target_path),
            "target_branch": branch,
            "journal_deltas": deltas,
            "salvage_required": True,
            "worktree_removed": False,
            "branch_deleted": False,
            "overall_ok": False,
        }
        print(json.dumps(payload, indent=2))
        return 1

    commit_sha = None
    if args.salvage_journal:
        commit_sha = salvage_journal(repo_root, target_path, branch, deltas, args.message, args.salvage_entry)
    worktree_removed, branch_deleted = remove_worktree_and_branch(repo_root, target_path, branch)
    payload = {
        "target_worktree": str(target_path),
        "target_branch": branch,
        "journal_deltas": deltas,
        "salvage_required": bool(deltas["all_paths"]),
        "salvage_commit_sha": commit_sha,
        "worktree_removed": worktree_removed,
        "branch_deleted": branch_deleted,
        "overall_ok": True,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
