import json
from typing import Optional

from ..fs_tools import FsLimits, ls_dir, glob_paths, read_text_file, grep_files
from ..config import settings


def tool_instructions() -> str:
    return (
        "You have access to filesystem tools via the backend. "
        "If you need to list/search/read files, respond ONLY with a single JSON object, no prose:\n"
        '{"tool":"ls|glob|grep|read","args":{...}}\n'
        "Tools:\n"
        '- ls: {"path":"relative/or/absolute"}\n'
        '- glob: {"pattern":"**/*.py","limit":200}\n'
        '- grep: {"path":".","query":"text","file_glob":"*.py","regex":false,"case_insensitive":true}\n'
        '- read: {"path":"backend_app/main.py","offset":1,"limit":200}\n'
        f"All paths must be under {settings.fs_root}. "
        "After receiving TOOL_RESULT, answer normally."
    )


def maybe_parse_tool_request(text: str) -> Optional[dict]:
    stripped = (text or "").strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return None
    try:
        obj = json.loads(stripped)
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    if "tool" not in obj or "args" not in obj:
        return None
    return obj


def execute_tool(tool_req: dict) -> dict:
    tool = tool_req.get("tool")
    args = tool_req.get("args") or {}
    limits = FsLimits(
        max_file_bytes_read=settings.fs_max_file_bytes_read,
        max_file_bytes_grep=settings.fs_max_file_bytes_grep,
        max_matches_grep=settings.fs_max_matches_grep,
    )

    if tool == "ls":
        return {"tool": "ls", "result": ls_dir(settings.fs_root, args.get("path", "."))}
    if tool == "glob":
        return {
            "tool": "glob",
            "result": glob_paths(
                settings.fs_root,
                args.get("pattern", "**/*"),
                limit=int(args.get("limit", 200)),
            ),
        }
    if tool == "read":
        return {
            "tool": "read",
            "result": read_text_file(
                settings.fs_root,
                args.get("path", ""),
                limits=limits,
                offset=int(args.get("offset", 1)),
                limit=int(args.get("limit", 200)),
            ),
        }
    if tool == "grep":
        return {
            "tool": "grep",
            "result": grep_files(
                settings.fs_root,
                args.get("path", "."),
                args.get("query", ""),
                limits=limits,
                file_glob=args.get("file_glob", "*"),
                regex=bool(args.get("regex", False)),
                case_insensitive=bool(args.get("case_insensitive", True)),
            ),
        }
    raise ValueError("Unknown tool")
