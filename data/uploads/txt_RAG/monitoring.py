import subprocess
import time
from dataclasses import dataclass
from typing import Optional

import psutil


@dataclass
class SystemStats:
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    gpu_util: Optional[float]
    gpu_vram_used_gb: Optional[float]
    gpu_vram_total_gb: Optional[float]


def get_amd_gpu_stats() -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Pobiera statystyki GPU AMD przez rocm-smi."""
    try:
        result = subprocess.run(
            ["rocm-smi", "--showuse", "--showmeminfo", "vram", "--csv"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode != 0:
            return None, None, None

        lines = result.stdout.strip().split("\n")
        if len(lines) < 2:
            return None, None, None

        gpu_util = None
        vram_used = None
        vram_total = None

        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                try:
                    util_str = parts[1].strip()
                    gpu_util = float(util_str) if util_str else None
                except (ValueError, IndexError):
                    pass

                try:
                    total_str = parts[2].strip()
                    vram_total = (
                        float(total_str) / 1024 / 1024 / 1024 if total_str else None
                    )
                except (ValueError, IndexError):
                    pass

                try:
                    used_str = parts[3].strip()
                    vram_used = (
                        float(used_str) / 1024 / 1024 / 1024 if used_str else None
                    )
                except (ValueError, IndexError):
                    pass

                if gpu_util is not None:
                    break

        return gpu_util, vram_used, vram_total

    except Exception:
        return None, None, None

        lines = result.stdout.strip().split("\n")
        if len(lines) < 2:
            return None, None, None

        gpu_util = None
        vram_used = None
        vram_total = None

        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) >= 5:
                try:
                    util_str = parts[2].strip().replace("%", "")
                    gpu_util = float(util_str) if util_str else None
                except (ValueError, IndexError):
                    pass

                try:
                    used_str = parts[3].strip()
                    vram_used = (
                        float(used_str) / 1024 / 1024 / 1024 if used_str else None
                    )
                except (ValueError, IndexError):
                    pass

                try:
                    total_str = parts[4].strip()
                    vram_total = (
                        float(total_str) / 1024 / 1024 / 1024 if total_str else None
                    )
                except (ValueError, IndexError):
                    pass

        return gpu_util, vram_used, vram_total

    except Exception:
        return None, None, None


def get_system_stats() -> SystemStats:
    """Pobiera pełne statystyki systemu."""
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    gpu_util, gpu_vram, gpu_total = get_amd_gpu_stats()

    return SystemStats(
        cpu_percent=cpu,
        ram_percent=ram.percent,
        ram_used_gb=ram.used / 1024 / 1024 / 1024,
        gpu_util=gpu_util,
        gpu_vram_used_gb=gpu_vram,
        gpu_vram_total_gb=gpu_total,
    )


def format_stats(stats: SystemStats) -> str:
    """Formatuje statystyki do logowania."""
    parts = [
        f"CPU: {stats.cpu_percent:.0f}%",
        f"RAM: {stats.ram_used_gb:.1f}GB ({stats.ram_percent:.0f}%)",
    ]

    if stats.gpu_util is not None:
        parts.append(f"GPU: {stats.gpu_util:.0f}%")
    if stats.gpu_vram_used_gb is not None and stats.gpu_vram_total_gb is not None:
        parts.append(
            f"VRAM: {stats.gpu_vram_used_gb:.1f}/{stats.gpu_vram_total_gb:.1f}GB"
        )

    return " | ".join(parts)


def log_stats(prefix: str = "") -> str:
    """Pobiera i formatuje statystyki - wygodna funkcja do logowania."""
    stats = get_system_stats()
    msg = format_stats(stats)
    if prefix:
        return f"{prefix}: {msg}"
    return msg
