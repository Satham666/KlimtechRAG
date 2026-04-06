#!/usr/bin/env python3
"""G3: System health check — diagnostyka runtime KlimtechRAG.

Sprawdza: Python, venv, porty, Qdrant, llama-server, GPU.
Wywolanie: python3 scripts/health_check.py
"""

import os
import socket
import subprocess
import sys


def _check(label: str, ok: bool, detail: str = "") -> str:
    icon = "\033[92mOK\033[0m" if ok else "\033[91mFAIL\033[0m"
    msg = f"  {icon}  {label}"
    if detail:
        msg += f" — {detail}"
    return msg


def check_python() -> str:
    version = sys.version.split()[0]
    return _check(f"Python {version}", True)


def check_venv() -> str:
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    if in_venv:
        return _check("Virtual environment", True, sys.prefix)
    return _check("Virtual environment", False, "NOT in venv")


def check_port(host: str, port: int) -> str:
    try:
        with socket.create_connection((host, port), timeout=2):
            return _check(f"Port {port}", True, f"{host}:{port}")
    except (socket.timeout, ConnectionRefusedError, OSError):
        return _check(f"Port {port}", False, f"{host}:{port} not responding")


def check_qdrant(url: str = "http://localhost:6333") -> str:
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"{url}/collections", timeout=3)
        if resp.status == 200:
            return _check("Qdrant", True, url)
    except Exception:
        pass
    return _check("Qdrant", False, url)


def check_llama_server(url: str = "http://localhost:8080") -> str:
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"{url}/health", timeout=3)
        if resp.status == 200:
            return _check("llama-server", True, url)
    except Exception:
        pass
    return _check("llama-server", False, f"{url} not responding (model not loaded?)")


def check_gpu() -> str:
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8080/gpu/status", timeout=3)
        if resp.status == 200:
            data = resp.read().decode()[:120]
            return _check("GPU status", True, data.strip())
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["rocm-smi", "--showproductname"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and "GPU" in result.stdout:
            line = result.stdout.strip().split("\n")[0]
            return _check("GPU (rocm-smi)", True, line.strip())
    except Exception:
        pass
    return _check("GPU", False, "rocm-smi not available, llama-server not running")


def check_backend(url: str = "https://192.168.31.70:8443") -> str:
    try:
        import ssl
        import urllib.request
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        resp = urllib.request.urlopen(f"{url}/health", timeout=3, context=ctx)
        if resp.status == 200:
            return _check("Backend (uvicorn)", True, url)
    except Exception:
        pass
    return _check("Backend (uvicorn)", False, url)


def check_env_file() -> str:
    candidates = [".env"]
    base = os.environ.get("KLIMTECH_BASE_PATH", "")
    if base:
        candidates.insert(0, os.path.join(base, ".env"))

    for c in candidates:
        if os.path.isfile(c):
            return _check(".env file", True, c)

    return _check(".env file", False, "not found")


def check_modules() -> str:
    required = ["fastapi", "haystack", "qdrant_client", "fitz"]
    missing = []
    for mod in required:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if not missing:
        return _check("Python modules", True, f"{len(required)} required")
    return _check("Python modules", False, f"missing: {', '.join(missing)}")


def main() -> None:
    print("\n" + "=" * 50)
    print("  KlimtechRAG Health Check")
    print("=" * 50 + "\n")

    checks = [
        ("Python & Environment", [check_python, check_venv, check_modules]),
        ("Network & Services", [
            lambda: check_port("localhost", 6333),
            lambda: check_qdrant(),
            lambda: check_port("localhost", 8080),
            lambda: check_llama_server(),
            lambda: check_backend(),
        ]),
        ("GPU & Hardware", [check_gpu]),
        ("Configuration", [check_env_file]),
    ]

    for section, funcs in checks:
        print(f"\n\033[1m{section}\033[0m")
        for fn in funcs:
            print(fn())

    print()


if __name__ == "__main__":
    main()
