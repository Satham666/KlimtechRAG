import whisper
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import tempfile
import os

router = APIRouter(tags=["whisper"])

_whisper_model = None


def get_whisper_model(size: str = "small"):
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(size, device="cuda")
    return _whisper_model


@router.post("/v1/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str = Form("whisper-1"),
    language: str = Form(None),
    response_format: str = Form("json"),
    prompt: str = Form(None),
):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    allowed_extensions = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".webm"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            400, f"Unsupported file format. Allowed: {allowed_extensions}"
        )

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        model = get_whisper_model()
        result = model.transcribe(
            tmp_path,
            language=language,
            prompt=prompt,
            fp16=True,
        )
        text = result["text"].strip()
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {str(e)}")
    finally:
        os.unlink(tmp_path)

    if response_format == "text":
        return text
    elif response_format == "verbose_json":
        return result
    return {"text": text}


@router.get("/whisper/models")
async def list_whisper_models():
    return {"models": whisper.available_models()}


@router.get("/whisper/status")
async def whisper_status():
    global _whisper_model
    return {
        "loaded": _whisper_model is not None,
        "device": "cuda" if _whisper_model else None,
    }
