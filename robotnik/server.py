"""Robotnik Server — wrapper dla llama-server (OpenAI-compatible HTTP).

Uruchamia Qwen2.5-Coder-3B-Q8_0 jako daemon HTTP na 127.0.0.1:8080.
Pozwala podpiąć model do OpenWebUI / Claude Code / skryptów Python.

CLI:
    python -m robotnik.server start
    python -m robotnik.server status
    python -m robotnik.server stop
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from robotnik.config import RobotnikConfig, detect_config

PID_FILE = Path("/tmp/robotnik_server.pid")
LOG_FILE = Path("/tmp/robotnik_server.log")


def build_server_cmd(config: RobotnikConfig) -> list[str]:
    """Flagi llama-server — odpowiednik Złotej Komendy bez --temp/top-k/top-p
    (te są ustawiane per-request w API).
    """
    return [
        str(config.binary_server),
        "-m", str(config.model_path),
        "--host", config.server_host,
        "--port", str(config.server_port),
        "-c", "4096",
        "-b", "64",
        "-ngl", "99",
        "-t", "8",
        "-tb", "12",
        "-fa", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
    ]


def is_running() -> tuple[bool, int | None]:
    if not PID_FILE.exists():
        return False, None
    try:
        pid = int(PID_FILE.read_text().strip())
    except ValueError:
        return False, None
    try:
        os.kill(pid, 0)
        return True, pid
    except ProcessLookupError:
        return False, pid


def health_check(config: RobotnikConfig, timeout: float = 2.0) -> bool:
    url = f"http://{config.server_host}:{config.server_port}/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def start(config: RobotnikConfig) -> int:
    running, pid = is_running()
    if running:
        print(f"Server already running (pid {pid})")
        return 0

    config.validate()
    cmd = build_server_cmd(config)
    log_fd = LOG_FILE.open("ab")
    proc = subprocess.Popen(
        cmd,
        stdout=log_fd,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    PID_FILE.write_text(str(proc.pid))
    print(f"Started llama-server pid={proc.pid}, log={LOG_FILE}")

    for _ in range(60):
        if health_check(config):
            print(f"Health OK: http://{config.server_host}:{config.server_port}")
            return 0
        time.sleep(1)
    print("Health check timeout — sprawdź log", file=sys.stderr)
    return 1


def stop() -> int:
    running, pid = is_running()
    if not running:
        print("Server not running")
        PID_FILE.unlink(missing_ok=True)
        return 0
    assert pid is not None
    os.kill(pid, signal.SIGTERM)
    for _ in range(10):
        try:
            os.kill(pid, 0)
            time.sleep(0.5)
        except ProcessLookupError:
            break
    else:
        os.kill(pid, signal.SIGKILL)
    PID_FILE.unlink(missing_ok=True)
    print(f"Stopped pid={pid}")
    return 0


def status(config: RobotnikConfig) -> int:
    running, pid = is_running()
    healthy = health_check(config) if running else False
    print(f"running: {running}, pid: {pid}, healthy: {healthy}")
    print(f"endpoint: http://{config.server_host}:{config.server_port}")
    return 0 if running and healthy else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Robotnik llama-server daemon")
    parser.add_argument("action", choices=["start", "stop", "status", "restart"])
    args = parser.parse_args()

    cfg = detect_config()

    if args.action == "start":
        return start(cfg)
    if args.action == "stop":
        return stop()
    if args.action == "status":
        return status(cfg)
    if args.action == "restart":
        stop()
        time.sleep(2)
        return start(cfg)
    return 2


if __name__ == "__main__":
    sys.exit(main())
