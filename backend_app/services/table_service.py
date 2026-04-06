import logging
import re
from typing import List, Optional

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Table Service — Table Structure Recognition (C3)
# Ekstrakcja tabel z PDF → Markdown. Uzywa PyMuPDF (fitz).
# ---------------------------------------------------------------------------


def extract_tables_from_pdf(file_path: str) -> List[dict]:
    """Ekstrahuje tabele z PDF jako Markdown stringi.

    Zwraca liste dicts: {"page": int, "markdown": str, "rows": int, "cols": int}.
    Pusta lista gdy brak PyMuPDF, brak tabel lub blad.
    """
    try:
        import fitz
    except ImportError:
        logger.debug("[C3] PyMuPDF niedostepny — TSR pominiety")
        return []

    tables: List[dict] = []

    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            tabs = page.find_tables()

            for tab_idx, tab in enumerate(tabs):
                try:
                    data = tab.extract()
                    if not data or len(data) < 2:
                        continue

                    num_rows = len(data)
                    num_cols = max(len(row) for row in data)

                    if num_rows < 2 or num_cols < 2:
                        continue

                    md_lines = _data_to_markdown(data)
                    markdown = "\n".join(md_lines)

                    if len(markdown.strip()) < 20:
                        continue

                    tables.append({
                        "page": page_num + 1,
                        "markdown": markdown,
                        "rows": num_rows,
                        "cols": num_cols,
                    })
                    logger.debug(
                        "[C3] Tabela str.%d: %dx%d (%d znakow)",
                        page_num + 1, num_rows, num_cols, len(markdown),
                    )
                except Exception as e:
                    logger.debug("[C3] Blad extrakcji tabeli str.%d: %s", page_num + 1, e)
                    continue

        doc.close()
    except Exception as e:
        logger.warning("[C3] Blad otwierania PDF: %s", e)

    logger.info("[C3] Znaleziono %d tabel w %s", len(tables), file_path)
    return tables


def _data_to_markdown(data: List[List]) -> List[str]:
    """Konwertuje 2D dane z PyMuPDF tabeli do Markdown table."""
    if not data:
        return []

    num_cols = max(len(row) for row in data)
    normalized = []
    for row in data:
        padded = list(row) + [""] * (num_cols - len(row))
        normalized.append([str(cell).strip() if cell else "" for cell in padded])

    lines: List[str] = []
    lines.append("| " + " | ".join(normalized[0]) + " |")
    lines.append("| " + " | ".join(["---"] * num_cols) + " |")

    for row in normalized[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return lines


def extract_tables_as_text(file_path: str) -> str:
    """Zwraca wszystkie tabele z PDF jako pojedynczy string w Markdown.

    Kazda tabela poprzedzona naglowkiem ze strony.
    Uzyteczne do dolaczenia do chunk context.
    """
    tables = extract_tables_from_pdf(file_path)
    if not tables:
        return ""

    parts: List[str] = ["\n\n## Tabele w dokumencie\n"]
    for i, tab in enumerate(tables):
        parts.append(f"### Tabela {i + 1} (strona {tab['page']}, {tab['rows']}x{tab['cols']})\n")
        parts.append(tab["markdown"])
        parts.append("")

    return "\n".join(parts)


def has_tables(file_path: str) -> bool:
    """Szybki check — czy PDF zawiera tabele."""
    tables = extract_tables_from_pdf(file_path)
    return len(tables) > 0
