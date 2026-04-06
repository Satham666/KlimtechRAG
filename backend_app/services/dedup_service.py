import hashlib

# ---------------------------------------------------------------------------
# Dedup Service — obliczanie hashy, wykrywanie duplikatów
# Wydzielony z routes/ingest.py (A1b refaktoryzacja)
# ---------------------------------------------------------------------------


def hash_bytes(data: bytes) -> str:
    """Oblicza SHA-256 hash z bajtów pliku."""
    return hashlib.sha256(data).hexdigest()


def hash_file(file_path: str) -> str:
    """Oblicza SHA-256 hash z zawartości pliku (streaming, bezpieczne dla dużych plików)."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_content_hash(text: str) -> str:
    """Oblicza SHA-256 hash z przetworzonego tekstu dokumentu (po parsowaniu, przed chunkingiem).

    Używany przez W3 Vector Cache — jeśli hash się nie zmienił,
    embeddingi są identyczne i można pominąć re-embedding.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
