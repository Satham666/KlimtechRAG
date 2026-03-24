"""
Handler do ekstrakcji i opisu obrazów z PDF.
Używa PyMuPDF do ekstrakcji i VLM (LFM2.5-VL) do opisu.
"""

import base64
import io
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import fitz

from ..prompts.vlm_prompts import get_full_prompt, get_vlm_params

logger = logging.getLogger("klimtechrag")

def _find_vlm_model():
    import glob
    from pathlib import Path
    
    paths_to_check = [
        os.environ.get("KLIMTECH_BASE_PATH", "").strip(),
        "/media/lobo/BACKUP/KlimtechRAG",
        str(Path.home() / "KlimtechRAG"),
    ]
    
    for base in paths_to_check:
        if not base:
            continue
        if not os.path.exists(base):
            continue
        hits = glob.glob(os.path.join(base, "modele_LLM", "model_video", "*.gguf"))
        hits = [f for f in hits if "mmproj" not in f]
        if hits:
            return hits[0]
    
    return ""
VLM_MODEL = _find_vlm_model()


def _find_llama_binary(name: str) -> str:
    """Szuka binarki llama w lokalizacjach opartych na KLIMTECH_BASE_PATH i ~/KlimtechRAG."""
    from ..config import settings
    candidates = [
        os.path.join(settings.base_path, "llama.cpp", "build", "bin", name),
        os.path.join(settings.base_path, "llama.cpp", name),
        os.path.expanduser(f"~/KlimtechRAG/llama.cpp/build/bin/{name}"),
        os.path.expanduser(f"~/KlimtechRAG/llama.cpp/{name}"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]  # fallback do pierwszego (błąd ujawni się przy uruchomieniu)


LLAMA_SERVER_BIN = _find_llama_binary("llama-server")
LLAMA_CLI_BIN = _find_llama_binary("llama-cli")
VLM_PORT = 8083
VLM_TIMEOUT = 60


@dataclass
class ExtractedImage:
    page_num: int
    image_index: int
    image_data: bytes
    width: int
    height: int
    description: Optional[str] = None
    image_type: str = "unknown"


def extract_images_from_pdf(pdf_path: str, min_size: int = 100) -> List[ExtractedImage]:
    """Ekstrahuje obrazy z PDF."""
    images = []

    try:
        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]

                try:
                    base_image = doc.extract_image(xref)
                    if not base_image:
                        continue

                    image_data = base_image["image"]
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)

                    if width < min_size or height < min_size:
                        continue

                    ext = base_image.get("ext", "png")

                    image_type = "photo"
                    if width > height * 2 or height > width * 2:
                        image_type = "diagram"
                    if ext in ["png", "svg"]:
                        image_type = "diagram"

                    images.append(
                        ExtractedImage(
                            page_num=page_num + 1,
                            image_index=img_index,
                            image_data=image_data,
                            width=width,
                            height=height,
                            image_type=image_type,
                        )
                    )

                except Exception as e:
                    logger.debug(
                        "Błąd ekstrakcji obrazu %d na stronie %d: %s",
                        img_index,
                        page_num,
                        e,
                    )
                    continue

        doc.close()

    except Exception as e:
        logger.error("Błąd otwierania PDF %s: %s", pdf_path, e)

    logger.info("Ekstrahowano %d obrazów z %s", len(images), os.path.basename(pdf_path))
    return images


def describe_image_with_vlm(image_path: str, prompt: str = None, image_type: str = "default") -> str:
    """Opisuje obraz używając VLM przez llama-cli."""

    if not os.path.exists(LLAMA_CLI_BIN):
        logger.error("llama-cli nie znaleziony: %s", LLAMA_CLI_BIN)
        return ""

    if not os.path.exists(VLM_MODEL):
        logger.error("Model VLM nie znaleziony: %s", VLM_MODEL)
        return ""

    if prompt is None:
        prompt = get_full_prompt(image_type)

    vlm_params = get_vlm_params()

    cmd = [
        LLAMA_CLI_BIN,
        "-m",
        VLM_MODEL,
        "--image",
        image_path,
        "-p",
        prompt,
        "-n",
        str(vlm_params["max_tokens"]),
        "--temp",
        str(vlm_params["temperature"]),
        "-ngl",
        str(vlm_params["gpu_layers"]),
        "-c",
        str(vlm_params["context_length"]),
        "--no-display",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=VLM_TIMEOUT,
            env={**os.environ, "HIP_VISIBLE_DEVICES": "0"},
        )

        output = result.stdout.strip()

        if "[/INST]" in output:
            output = output.split("[/INST]")[-1].strip()
        if "<|eot_id|>" in output:
            output = output.split("<|eot_id|>")[0].strip()

        return output

    except subprocess.TimeoutExpired:
        logger.warning("Timeout VLM dla obrazu: %s", image_path)
        return ""
    except Exception as e:
        logger.error("Błąd VLM: %s", e)
        return ""


def describe_image_with_vlm_server(
    image_data: bytes, prompt: str = None, vlm_url: str = None, image_type: str = "default"
) -> str:
    """Opisuje obraz używając VLM przez HTTP API (jeśli VLM server działa)."""

    import requests

    if vlm_url is None:
        vlm_url = f"http://localhost:{VLM_PORT}/v1/chat/completions"

    if prompt is None:
        prompt = get_full_prompt(image_type)

    vlm_params = get_vlm_params()

    image_base64 = base64.b64encode(image_data).decode("utf-8")

    payload = {
        "model": "vlm",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ],
            }
        ],
        "max_tokens": vlm_params["max_tokens"],
        "temperature": vlm_params["temperature"],
    }

    try:
        response = requests.post(vlm_url, json=payload, timeout=VLM_TIMEOUT)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            logger.warning("VLM server error: %d", response.status_code)
            return ""
    except Exception as e:
        logger.debug("VLM server niedostępny: %s", e)
        return ""


def process_pdf_with_images(
    pdf_path: str,
    extract_images: bool = True,
    describe_images: bool = True,
    min_image_size: int = 100,
    max_images: int = 20,
    use_vlm_server: bool = False,
) -> dict:
    """
    Przetwarza PDF: tekst + obrazy z opisami.

    Returns:
        dict z:
        - text: str - tekst z PDF
        - images: List[dict] - lista obrazów z opisami
        - combined_content: str - połączony tekst + opisy obrazów
    """

    result = {
        "text": "",
        "images": [],
        "combined_content": "",
    }

    text = extract_pdf_text_simple(pdf_path)
    result["text"] = text

    if not extract_images:
        result["combined_content"] = text
        return result

    images = extract_images_from_pdf(pdf_path, min_size=min_image_size)

    if not images:
        result["combined_content"] = text
        return result

    images = images[:max_images]

    pdf_name = os.path.basename(pdf_path)
    image_descriptions = []

    for img in images:
        img_info = {
            "page": img.page_num,
            "index": img.image_index,
            "width": img.width,
            "height": img.height,
            "type": img.image_type,
            "description": "",
        }

        if describe_images:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(img.image_data)
                tmp_path = tmp.name

            try:
                if use_vlm_server:
                    desc = describe_image_with_vlm_server(img.image_data, image_type=img.image_type)
                else:
                    desc = describe_image_with_vlm(tmp_path, image_type=img.image_type)

                img_info["description"] = desc
                img.description = desc

                if desc:
                    image_descriptions.append(
                        f"\n[OBRAZ ze strony {img.page_num}, typ: {img.image_type}]\n{desc}\n"
                    )

            finally:
                os.unlink(tmp_path)

        result["images"].append(img_info)

    combined = text
    if image_descriptions:
        combined += "\n\n--- OBRAZY Z DOKUMENTU ---\n" + "".join(image_descriptions)

    result["combined_content"] = combined

    logger.info(
        "PDF %s: tekst=%d znaków, obrazy=%d, opisy=%d",
        pdf_name,
        len(text),
        len(images),
        len([d for d in image_descriptions if d]),
    )

    return result


def extract_pdf_text_simple(pdf_path: str) -> str:
    """Prosta ekstrakcja tekstu z PDF przez pdftotext."""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout.strip()
    except Exception as e:
        logger.warning("pdftotext failed: %s", e)
        return ""


def start_vlm_server():
    """Uruchamia VLM server na porcie 8083."""
    import requests

    try:
        r = requests.get(f"http://localhost:{VLM_PORT}/health", timeout=1)
        if r.status_code == 200:
            logger.info("VLM server już działa")
            return True
    except Exception:
        pass

    if not os.path.exists(VLM_MODEL):
        logger.error("Model VLM nie znaleziony: %s", VLM_MODEL)
        return False

    cmd = [
        LLAMA_SERVER_BIN,
        "-m",
        VLM_MODEL,
        "--host",
        "0.0.0.0",
        "--port",
        str(VLM_PORT),
        "-ngl",
        "99",
        "-c",
        "4096",
        "--log-disable",
    ]

    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env={**os.environ, "HIP_VISIBLE_DEVICES": "0"},
    )

    import time

    for _ in range(30):
        time.sleep(1)
        try:
            r = requests.get(f"http://localhost:{VLM_PORT}/health", timeout=1)
            if r.status_code == 200:
                logger.info("VLM server uruchomiony na porcie %d", VLM_PORT)
                return True
        except Exception:
            continue

    logger.error("VLM server nie wystartował")
    return False


def stop_vlm_server():
    """Zatrzymuje VLM server."""
    subprocess.run(["pkill", "-f", f"llama-server.*{VLM_PORT}"], capture_output=True)
