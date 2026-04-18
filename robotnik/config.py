"""Konfiguracja Robotnika — Złota Komenda v1.0 dla Quadro P1000 (Pascal 4GB).

Ustalono eksperymentalnie (patrz GPU_LAPTOPT_TEST.md):
- Prompt: 286 t/s, Generation: 14.1 t/s, EOS natural, brak OOM
- Kontekst 4096 mieści się w 4GB VRAM dzięki -fa on + KV quant q8_0
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RobotnikConfig:
    """Pełna konfiguracja robotnika: binarka + model + flagi."""

    binary_cli: Path
    binary_server: Path
    model_path: Path
    flags: list[str] = field(default_factory=list)
    server_port: int = 8080
    server_host: str = "127.0.0.1"

    def validate(self) -> None:
        for name, path in (
            ("binary_cli", self.binary_cli),
            ("binary_server", self.binary_server),
            ("model_path", self.model_path),
        ):
            if not path.exists():
                raise FileNotFoundError(f"{name} not found: {path}")


LAPTOP_CONFIG = RobotnikConfig(
    binary_cli=Path("/home/tamiel/programy/llama.cpp/build/bin/llama-cli"),
    binary_server=Path("/home/tamiel/programy/llama.cpp/build/bin/llama-server"),
    model_path=Path(
        "/home/tamiel/.cache/llama.cpp/"
        "lmstudio-community_Qwen2.5-Coder-3B-GGUF_Qwen2.5-Coder-3B-Q8_0.gguf"
    ),
    flags=[
        "-c", "4096",
        "-n", "-1",
        "-b", "64",
        "-ngl", "99",
        "-t", "8",
        "-tb", "12",
        "-fa", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "--temp", "0.6",
        "--top-k", "40",
        "--top-p", "0.9",
        "--repeat-penalty", "1.1",
    ],
)

PROXMOX_CONFIG = RobotnikConfig(
    binary_cli=Path("/opt/llama.cpp/build/bin/llama-cli"),
    binary_server=Path("/opt/llama.cpp/build/bin/llama-server"),
    model_path=Path("/opt/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"),
    flags=[
        "-c", "8192",
        "-n", "-1",
        "-b", "128",
        "-ngl", "99",
        "-t", "8",
        "-tb", "16",
        "-fa", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "--temp", "0.6",
        "--top-k", "40",
        "--top-p", "0.9",
        "--repeat-penalty", "1.1",
    ],
)

AMD_ROCM_ENV = {
    "HIP_VISIBLE_DEVICES": "0",
    "GPU_MAX_ALLOC_PERCENT": "100",
    "HSA_ENABLE_SDMA": "0",
    "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
}


def detect_config() -> RobotnikConfig:
    """Wybiera config na podstawie env ROBOTNIK_PROFILE lub fallback na laptop."""
    profile = os.getenv("ROBOTNIK_PROFILE", "laptop").lower()
    if profile == "proxmox":
        return PROXMOX_CONFIG
    return LAPTOP_CONFIG
