import fnmatch
import glob
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class FsSecurityError(Exception):
    pass


@dataclass(frozen=True)
class FsLimits:
    max_file_bytes_read: int
    max_file_bytes_grep: int
    max_matches_grep: int


def _real(path: str) -> str:
    return os.path.realpath(path)


def resolve_path(fs_root: str, user_path: str) -> str:
    """Zamienia user_path na realpath i sprawdza, czy jest pod fs_root."""
    base_root = _real(fs_root)
    raw_path = os.path.expanduser(user_path or ".")

    if os.path.isabs(raw_path):
        candidate = _real(raw_path)
    else:
        candidate = _real(os.path.join(base_root, raw_path))

    if not candidate.startswith(base_root):
        raise FsSecurityError("Path not allowed")
    return candidate


def ls_dir(fs_root: str, user_path: str, timeout_seconds: int = 5) -> Dict[str, Any]:
    path = resolve_path(fs_root, user_path)
    result = subprocess.run(
        ["ls", "-la", path],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    return {
        "path": path,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def glob_paths(fs_root: str, pattern: str, limit: int = 200) -> Dict[str, Any]:
    """Wyszukuje ścieżki za pomocą pythonowego glob (recursive)."""
    base_root = _real(fs_root)
    raw_pattern = pattern or "**/*"

    if os.path.isabs(raw_pattern):
        pattern_abs = raw_pattern
    else:
        pattern_abs = os.path.join(base_root, raw_pattern)

    matches = glob.glob(pattern_abs, recursive=True)
    safe_matches: List[str] = []
    for m in matches:
        rm = _real(m)
        if rm.startswith(base_root):
            safe_matches.append(rm)
        if len(safe_matches) >= limit:
            break

    return {
        "pattern": raw_pattern,
        "matches": safe_matches,
        "truncated": len(matches) > limit,
    }


def read_text_file(
    fs_root: str,
    user_path: str,
    limits: FsLimits,
    offset: int = 1,
    limit: int = 200,
) -> Dict[str, Any]:
    path = resolve_path(fs_root, user_path)

    size = os.path.getsize(path)
    if size > limits.max_file_bytes_read:
        raise FsSecurityError(f"File too large to read ({size} bytes)")

    # offset jest 1-indexed
    start = max(offset, 1)
    max_lines = max(limit, 1)

    lines_out: List[str] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, start=1):
            if i < start:
                continue
            lines_out.append(f"{i}|{line.rstrip()}")
            if len(lines_out) >= max_lines:
                break

    return {
        "path": path,
        "size_bytes": size,
        "offset": start,
        "limit": max_lines,
        "lines": lines_out,
    }


def grep_files(
    fs_root: str,
    user_path: str,
    query: str,
    limits: FsLimits,
    file_glob: str = "*",
    regex: bool = False,
    case_insensitive: bool = True,
) -> Dict[str, Any]:
    root = resolve_path(fs_root, user_path)
    if not query:
        raise ValueError("query is required")

    flags = re.IGNORECASE if case_insensitive else 0
    if regex:
        pattern = re.compile(query, flags=flags)
    else:
        pattern = re.compile(re.escape(query), flags=flags)

    matches: List[Dict[str, Any]] = []
    scanned_files = 0
    skipped_large = 0

    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if not fnmatch.fnmatch(name, file_glob):
                continue
            file_path = os.path.join(dirpath, name)

            try:
                size = os.path.getsize(file_path)
            except OSError:
                continue

            if size > limits.max_file_bytes_grep:
                skipped_large += 1
                continue

            scanned_files += 1
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    for line_no, line in enumerate(f, start=1):
                        if pattern.search(line):
                            matches.append(
                                {
                                    "path": _real(file_path),
                                    "line": line_no,
                                    "text": line.rstrip(),
                                }
                            )
                            if len(matches) >= limits.max_matches_grep:
                                return {
                                    "root": root,
                                    "query": query,
                                    "file_glob": file_glob,
                                    "regex": regex,
                                    "case_insensitive": case_insensitive,
                                    "scanned_files": scanned_files,
                                    "skipped_large_files": skipped_large,
                                    "matches": matches,
                                    "truncated": True,
                                }
            except OSError:
                continue

    return {
        "root": root,
        "query": query,
        "file_glob": file_glob,
        "regex": regex,
        "case_insensitive": case_insensitive,
        "scanned_files": scanned_files,
        "skipped_large_files": skipped_large,
        "matches": matches,
        "truncated": False,
    }
