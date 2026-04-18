"""Robotnik Runner — subprocess wrapper dla llama-cli.

Wywołanie:
    from robotnik.runner import run_task
    output = run_task(Path("robotnik_tasks/001_wireguard.md"))

CLI:
    python -m robotnik.runner robotnik_tasks/001_wireguard.md
    python -m robotnik.runner robotnik_tasks/001_wireguard.md --out out.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from robotnik.config import RobotnikConfig, detect_config


def build_cmd(prompt_file: Path, config: RobotnikConfig) -> list[str]:
    """Buduje listę argumentów dla subprocess.run — zawsze lista, nigdy shell=True."""
    return [
        str(config.binary_cli),
        "-m", str(config.model_path),
        *config.flags,
        "-f", str(prompt_file),
    ]


def run_task(
    prompt_file: Path,
    config: RobotnikConfig | None = None,
    stream: bool = True,
) -> str:
    """Uruchamia robotnika z promptem z pliku, zwraca stdout.

    stream=True  — wyjście idzie live do stdout (CLI tryb, brak capture)
    stream=False — capture stdout do str (programmatic tryb)
    """
    cfg = config or detect_config()
    cfg.validate()

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    cmd = build_cmd(prompt_file, cfg)

    if stream:
        subprocess.run(cmd, check=True)
        return ""

    result = subprocess.run(
        cmd, check=True, capture_output=True, text=True
    )
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Robotnik — lokalny LLM executor (Qwen via llama-cli)"
    )
    parser.add_argument(
        "prompt_file", type=Path, help="Ścieżka do pliku z promptem"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Zapisz output do pliku zamiast stdout (wymusza stream=False)",
    )
    args = parser.parse_args()

    try:
        if args.out is not None:
            output = run_task(args.prompt_file, stream=False)
            args.out.write_text(output, encoding="utf-8")
            print(f"Output saved: {args.out}", file=sys.stderr)
        else:
            run_task(args.prompt_file, stream=True)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print(f"llama-cli failed with code {e.returncode}", file=sys.stderr)
        return e.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
