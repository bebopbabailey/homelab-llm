#!/usr/bin/env python3
"""Create a filesystem-based review snapshot ZIP for the repo and copy it to Studio."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import fnmatch
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import zipfile


EXCLUDED_DIR_NAMES = {
    ".cache",
    ".git",
    ".idea",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".turbo",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "venv",
}
EXCLUDED_PATH_PREFIXES = (
    "evals/websearch/artifacts/",
    "homelab-llm-agent-snapshot/",
)
EXCLUDED_FILE_PATTERNS = (
    "*.log",
    "*.pyc",
    "*.pyo",
    "*.sqlite*",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
    "*.tmp",
    "*.zip",
)
EXCLUDED_EXACT_FILES = {
    ".git",
    "homelab-llm-agent-snapshot.zip",
}


@dataclass(frozen=True)
class FileEntry:
    relpath: str
    source_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a review snapshot ZIP of the repo as it exists on disk and copy it to studio:~/."
    )
    parser.add_argument(
        "--output",
        help="Local ZIP path. Defaults to /tmp/<repo>-review-snapshot-<timestamp>.zip",
    )
    parser.add_argument(
        "--remote",
        default="studio:~/",
        help="Remote copy target for scp (default: studio:~/)",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Create the local ZIP only and skip the scp step.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved plan without creating or copying the ZIP.",
    )
    return parser.parse_args()


def require_command(name: str) -> None:
    if shutil.which(name):
        return
    raise SystemExit(f"error: required command not found in PATH: {name}")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def archive_base_name(repo_root: Path) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{repo_root.name}-review-snapshot-{stamp}"


def resolve_output_path(repo_root: Path, output: str | None) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    return Path("/tmp") / f"{archive_base_name(repo_root)}.zip"


def normalize_relpath(path: PurePosixPath) -> str:
    text = path.as_posix()
    return "" if text == "." else text.strip("/")


def is_excluded_dir_name(name: str) -> bool:
    return name in EXCLUDED_DIR_NAMES or name.startswith(".venv") or name.startswith("venv")


def matches_excluded_prefix(normalized: str) -> bool:
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in EXCLUDED_PATH_PREFIXES)


def should_exclude_dir(relative_dir: PurePosixPath) -> bool:
    normalized = normalize_relpath(relative_dir)
    if not normalized:
        return False
    if any(is_excluded_dir_name(part) for part in relative_dir.parts):
        return True
    return matches_excluded_prefix(normalized)


def should_exclude_file(relative_file: PurePosixPath) -> bool:
    normalized = normalize_relpath(relative_file)
    if not normalized:
        return False
    if matches_excluded_prefix(normalized):
        return True

    basename = relative_file.name
    if basename in EXCLUDED_EXACT_FILES:
        return True
    for pattern in EXCLUDED_FILE_PATTERNS:
        if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(normalized, pattern):
            return True
    return False


def is_within_repo(path: Path, repo_root: Path) -> bool:
    try:
        path.relative_to(repo_root)
    except ValueError:
        return False
    return True


def collect_entries(repo_root: Path, output_path: Path) -> tuple[list[FileEntry], list[str]]:
    excluded_paths: list[str] = []
    entries: list[FileEntry] = []
    output_in_repo = is_within_repo(output_path, repo_root)

    for current_root, dirnames, filenames in os.walk(repo_root, topdown=True, followlinks=False):
        current_dir = Path(current_root)
        relative_dir = PurePosixPath(current_dir.relative_to(repo_root).as_posix())

        kept_dirnames: list[str] = []
        for dirname in sorted(dirnames):
            relative_path = relative_dir / dirname
            if should_exclude_dir(relative_path):
                excluded_paths.append(f"{normalize_relpath(relative_path)}/")
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in sorted(filenames):
            source_path = current_dir / filename
            if output_in_repo and source_path.resolve() == output_path:
                excluded_paths.append(normalize_relpath(relative_dir / filename))
                continue

            relative_file = relative_dir / filename
            if should_exclude_file(relative_file):
                excluded_paths.append(normalize_relpath(relative_file))
                continue

            entries.append(
                FileEntry(
                    relpath=normalize_relpath(relative_file),
                    source_path=source_path,
                )
            )

    entries.sort(key=lambda item: item.relpath)
    excluded_paths = sorted(path for path in set(excluded_paths) if path)
    return entries, excluded_paths


def human_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{num_bytes}B"


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_zip(entries: list[FileEntry], output_path: Path, prefix: str) -> tuple[int, int, list[str]]:
    ensure_parent_dir(output_path)
    written = 0
    skipped_paths: list[str] = []
    total = len(entries)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in entries:
            if not entry.source_path.exists() or not entry.source_path.is_file():
                skipped_paths.append(entry.relpath)
                continue
            archive.write(entry.source_path, arcname=f"{prefix}/{entry.relpath}")
            written += 1
            if written == 1 or written % 250 == 0 or written == total:
                print(f"progress: zipped {written}/{total} files", file=sys.stderr)
    return written, output_path.stat().st_size, skipped_paths


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def remote_verify_command(remote_path: str) -> str:
    if remote_path == "~":
        path_expr = '"$HOME"'
    elif remote_path.startswith("~/"):
        suffix = remote_path[2:]
        path_expr = f'"$HOME/{suffix}"'
    else:
        path_expr = shell_quote(remote_path)
    return f"target_path={path_expr}; test -f \"$target_path\" && ls -lh \"$target_path\""


def remote_result_path(remote_target: str, filename: str) -> tuple[str, str]:
    if ":" not in remote_target:
        raise SystemExit(f"error: remote target must be in scp host:path form, got: {remote_target}")
    host, remote_path = remote_target.split(":", 1)
    if not host or not remote_path:
        raise SystemExit(f"error: invalid remote target: {remote_target}")

    normalized = remote_path
    if normalized in {"~", ".", "./"}:
        normalized = f"{normalized.rstrip('/')}/{filename}"
    elif normalized.endswith("/"):
        normalized = f"{normalized}{filename}"
    return host, normalized


def copy_remote(output_path: Path, remote_target: str) -> str:
    host, remote_path = remote_result_path(remote_target, output_path.name)
    subprocess.run(["scp", str(output_path), remote_target], check=True)
    subprocess.run(["ssh", host, remote_verify_command(remote_path)], check=True)
    return f"{host}:{remote_path}"


def print_dry_run(repo_root: Path, output_path: Path, remote_target: str, entries: list[FileEntry], excluded: list[str]) -> None:
    print(f"repo_root: {repo_root}")
    print(f"output_path: {output_path}")
    print(f"remote_target: {remote_target}")
    print(f"include_count: {len(entries)}")
    print(f"excluded_count: {len(excluded)}")
    if excluded:
        print("excluded_examples:")
        for path in excluded[:10]:
            print(f"  - {path}")


def main() -> int:
    args = parse_args()
    if not args.no_copy:
        require_command("scp")

    repo_root = repo_root_from_script()
    output_path = resolve_output_path(repo_root, args.output)
    entries, excluded = collect_entries(repo_root, output_path)

    if args.dry_run:
        print_dry_run(repo_root, output_path, args.remote, entries, excluded)
        return 0

    prefix = output_path.stem
    print(f"collect_complete: {len(entries)} files, {len(excluded)} excluded", file=sys.stderr)
    written, size_bytes, skipped_paths = write_zip(entries, output_path, prefix)
    for relpath in skipped_paths:
        print(f"warning: skipped disappearing file during archive creation: {relpath}", file=sys.stderr)

    print(f"created_zip: {output_path}")
    print(f"archive_root: {prefix}/")
    print(f"file_count: {written}")
    print(f"zip_size: {human_size(size_bytes)}")
    print(f"excluded_count: {len(excluded)}")

    if args.no_copy:
        print("remote_copy: skipped (--no-copy)")
        return 0

    remote_location = copy_remote(output_path, args.remote)
    print(f"remote_copy: {remote_location}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
