"""
Model Selector — Inteligentne wybranie embeddera na podstawie typu pliku.

Obsługuje:
- Visual: PDF scany, obrazy (ColPali)
- Text: dokumenty, markdown (e5-large)
- Code: skrypty, konfiguracje (bge-large-en-v1.5)
- Audio: [PLACEHOLDER — do implementacji]
- Video: [PLACEHOLDER — do implementacji]
"""

from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger("klimtechrag")

# ═══════════════════════════════════════════════════════════════════════════
# MODEL METADATA
# ═══════════════════════════════════════════════════════════════════════════

MODELS: Dict[str, Dict] = {
    # ──── VISUAL EMBEDDINGS ────
    "colpali": {
        "name": "vidore/colpali-v1.3-hf",
        "dimension": 128,
        "vram_mb": 7000,
        "type": "visual",
        "description": "Visual embeddings dla skanów PDF i obrazów",
        "extensions": {
            ".pdf",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".svg"
        },
    },

    # ──── SEMANTIC TEXT EMBEDDINGS ────
    "e5-large": {
        "name": "intfloat/multilingual-e5-large",
        "dimension": 1024,
        "vram_mb": 2000,
        "type": "semantic",
        "description": "Semantic embeddings dla tekstu, dokumentów, danych",
        "extensions": {
            ".txt", ".md", ".rst", ".markdown",
            ".docx", ".doc", ".odt", ".rtf",
            ".csv", ".tsv", ".xlsx", ".xls", ".ods",
            ".sql", ".sqlite", ".sqlite3",
            ".tar", ".tar.gz", ".tar.bz2", ".zip", ".7z", ".gz", ".bz2",
            ".pkl", ".pickle", ".h5", ".hdf5", ".parquet", ".avro"
        },
    },

    # ──── CODE & STRUCTURED EMBEDDINGS ────
    "bge-large-en-v1.5": {
        "name": "BAAI/bge-large-en-v1.5",
        "dimension": 1024,
        "vram_mb": 2000,
        "type": "code",
        "description": "Code-aware embeddings dla kodu, JSON, XML, markup",
        "extensions": {
            # Python
            ".py", ".pyc", ".pyx",
            # Shell
            ".sh", ".bash", ".zsh", ".fish", ".ksh",
            # JavaScript/TypeScript
            ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
            # Java/JVM
            ".java", ".kt", ".scala", ".groovy", ".gradle",
            # C/C++
            ".cpp", ".c", ".h", ".hpp", ".cc", ".cxx", ".c++", ".C",
            # Go
            ".go",
            # Rust
            ".rs", ".rust",
            # PHP
            ".php", ".phtml",
            # Ruby
            ".rb", ".ruby", ".erb",
            # C#
            ".cs", ".csharp",
            # Swift
            ".swift",
            # Perl
            ".pl", ".pm",
            # R
            ".r", ".R",
            # Objective-C
            ".m", ".mm", ".objective-c",
            # Dart
            ".dart",
            # Lua
            ".lua",
            # JSON/YAML/TOML
            ".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg",
            # XML
            ".xml", ".xsl", ".soap",
            # Markup
            ".html", ".htm", ".xhtml",
            ".css", ".scss", ".sass", ".less", ".stylus",
            ".haml", ".jade", ".pug",
            ".mustache", ".handlebars", ".hbs", ".ejs",
            ".jinja", ".jinja2", ".j2",
            ".freemarker", ".ftl",
            ".liquid", ".erb", ".eruby",
            ".tpl", ".template",
            # Config
            ".dockerfile", ".nginx",
            # Protobuf
            ".proto", ".protobuf",
        },
    },

    # ──── AUDIO EMBEDDINGS [PLACEHOLDER] ────
    "audio-embedder": {
        "name": "[TBD] audio-embedder-model",
        "dimension": None,
        "vram_mb": None,
        "type": "audio",
        "description": "Audio embeddings dla muzyki, mowy, soundów [DO IMPLEMENTACJI]",
        "extensions": {
            ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wma", ".ape"
        },
        "status": "NOT_IMPLEMENTED",
        "notes": "Candidates: wav2vec2, HuBERT, WavLM, Whisper-embedding",
    },

    # ──── VIDEO EMBEDDINGS [PLACEHOLDER] ────
    "video-embedder": {
        "name": "[TBD] video-embedder-model",
        "dimension": None,
        "vram_mb": None,
        "type": "video",
        "description": "Multimodal embeddings dla video (frames + audio) [DO IMPLEMENTACJI]",
        "extensions": {
            ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".3gp", ".m4v"
        },
        "status": "NOT_IMPLEMENTED",
        "notes": "Candidates: CLIP video, ViViT, TimeSformer, VideoMAE",
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def select_model_for_file(file_path: str) -> str:
    """
    Wybiera model embeddingu na podstawie rozszerzenia pliku.

    Args:
        file_path: ścieżka do pliku (np. "/path/to/document.pdf")

    Returns:
        Nazwa modelu: "colpali", "e5-large", "bge-large-en-v1.5", "audio-embedder", "video-embedder"

    Raises:
        ValueError: jeśli plik ma nieznaną zawartość lub placeholdera (audio/video)
    """
    ext = Path(file_path).suffix.lower()

    # Przeszukaj modele
    for model_name, metadata in MODELS.items():
        if ext in metadata["extensions"]:
            # Sprawdź czy model jest zaimplementowany
            if metadata.get("status") == "NOT_IMPLEMENTED":
                logger.warning(
                    f"Model '{model_name}' dla rozszerzenia {ext} nie jest jeszcze "
                    f"zaimplementowany. Fallback do e5-large."
                )
                return "e5-large"
            return model_name

    # Fallback do e5-large dla nieznanych rozszerzeń
    logger.info(f"Nieznane rozszerzenie {ext}, fallback do e5-large")
    return "e5-large"


def get_model_metadata(model_name: str) -> Dict:
    """
    Zwraca metadane modelu (wymiar, VRAM, typ, opis).

    Args:
        model_name: nazwa modelu (np. "colpali", "e5-large")

    Returns:
        Słownik z metadanymi modelu
    """
    return MODELS.get(model_name, MODELS["e5-large"])


def is_model_implemented(model_name: str) -> bool:
    """Sprawdza czy model jest zaimplementowany (nie placeholder)."""
    metadata = MODELS.get(model_name)
    return metadata and metadata.get("status") != "NOT_IMPLEMENTED"


def get_file_type(file_path: str) -> str:
    """
    Zwraca typ pliku: "visual", "semantic", "code", "audio", "video".

    Args:
        file_path: ścieżka do pliku

    Returns:
        Typ: "visual" | "semantic" | "code" | "audio" | "video"
    """
    model_name = select_model_for_file(file_path)
    metadata = get_model_metadata(model_name)
    return metadata.get("type", "unknown")


def get_compatible_models(file_type: str) -> List[str]:
    """
    Zwraca listę modeli kompatybilnych z typem pliku.

    Args:
        file_type: "visual", "semantic", "code", "audio", "video"

    Returns:
        Lista nazw modeli
    """
    return [name for name, meta in MODELS.items() if meta.get("type") == file_type]


def validate_file_extension(file_path: str) -> bool:
    """Sprawdza czy rozszerzenie pliku jest obsługiwane."""
    ext = Path(file_path).suffix.lower()
    for metadata in MODELS.values():
        if ext in metadata.get("extensions", set()):
            return True
    return False


def get_extension_suggestions(ext: str) -> Optional[str]:
    """
    Sugeruje obsługiwane rozszerzenie podobne do danego.
    Przydatne do diagnozowania błędów użytkownika.

    Args:
        ext: rozszerzenie (np. ".txt")

    Returns:
        Sugestia lub None
    """
    from difflib import get_close_matches

    all_exts = []
    for metadata in MODELS.values():
        all_exts.extend(metadata.get("extensions", []))

    matches = get_close_matches(ext, all_exts, n=1, cutoff=0.6)
    return matches[0] if matches else None


def get_supported_extensions() -> Dict[str, List[str]]:
    """Zwraca wszystkie obsługiwane rozszerzenia pogrupowane po modelu."""
    return {
        model_name: sorted(list(meta.get("extensions", [])))
        for model_name, meta in MODELS.items()
    }


def log_model_selection_info():
    """Loguje informacje o dostępnych modelach."""
    logger.info("═" * 80)
    logger.info("MODEL SELECTION CONFIGURATION")
    logger.info("═" * 80)

    for model_name, metadata in MODELS.items():
        status = "✅ READY" if is_model_implemented(model_name) else "⏳ PLACEHOLDER"
        logger.info(
            f"{status} | {model_name:25s} | {metadata['type']:10s} | "
            f"Dim: {metadata.get('dimension', '?')}, VRAM: {metadata.get('vram_mb', '?')}MB"
        )

    logger.info("═" * 80)


# Loguj konfigurację przy imporcie
log_model_selection_info()
