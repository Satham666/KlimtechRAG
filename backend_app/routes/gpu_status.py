"""
routes/gpu_status.py — Monitoring GPU (rocm-smi)
=================================================
GET /gpu/status — zwraca JSON z temperaturą, użyciem GPU i VRAM
"""

import subprocess
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["gpu"])


def _parse_rocm_smi() -> dict:
    """Wywołuje rocm-smi i parsuje wynik do dict."""
    gpus = {}

    # Temperatura + użycie GPU
    try:
        r = subprocess.run(
            ["rocm-smi", "--showtemp", "--showuse", "--showmeminfo", "vram", "--csv"],
            capture_output=True, text=True, timeout=3
        )
        if r.returncode != 0:
            return {"error": "rocm-smi failed", "stderr": r.stderr[:200]}

        lines = [l for l in r.stdout.strip().split("\n") if l and not l.startswith("WARNING")]
        if len(lines) < 2:
            return {"error": "No GPU data"}

        header = [h.strip().lower() for h in lines[0].split(",")]
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < len(header):
                continue

            row = dict(zip(header, parts))
            device = row.get("device", "?")

            gpu = {
                "device": device,
                "temp_c": None,
                "gpu_use_percent": None,
                "vram_total_gb": None,
                "vram_used_gb": None,
                "vram_percent": None,
            }

            # Temperatura
            for key in row:
                if "temperature" in key and "edge" in key:
                    try:
                        gpu["temp_c"] = round(float(row[key]), 1)
                    except (ValueError, TypeError):
                        pass

            # GPU use %
            for key in row:
                if "gpu use" in key or "gpu_use" in key:
                    try:
                        val = row[key].replace("%", "").strip()
                        gpu["gpu_use_percent"] = round(float(val), 1)
                    except (ValueError, TypeError):
                        pass

            # VRAM - check "used" first (more specific match)
            for key in row:
                if "vram total used" in key:
                    try:
                        gpu["vram_used_gb"] = round(float(row[key]) / (1024**3), 2)
                    except (ValueError, TypeError):
                        pass
                elif "vram total" in key:
                    try:
                        gpu["vram_total_gb"] = round(float(row[key]) / (1024**3), 2)
                    except (ValueError, TypeError):
                        pass

            if gpu["vram_total_gb"] and gpu["vram_used_gb"]:
                gpu["vram_percent"] = round(
                    gpu["vram_used_gb"] / gpu["vram_total_gb"] * 100, 1
                )

            gpus[device] = gpu

    except subprocess.TimeoutExpired:
        return {"error": "rocm-smi timeout"}
    except FileNotFoundError:
        return {"error": "rocm-smi not found"}
    except Exception as e:
        return {"error": str(e)}

    return gpus


@router.get("/gpu/status")
async def gpu_status():
    """Zwraca status GPU (temperatura, użycie, VRAM)."""
    data = _parse_rocm_smi()
    return JSONResponse(content=data)
