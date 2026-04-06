import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Layout Service — rozpoznawanie struktury PDF (C1)
# Implementacja: PyMuPDF heurystyki (bez zewnętrznego modelu ML)
# Klasyfikuje regiony: text, header, footer, image, table_hint
#
# Architektura:
#   parse_pdf_layout(pdf_path) → List[PageRegion]
#   regions_to_text_chunks(regions) → tekst bez nagłówków/stopek
#
# Przyszłe rozszerzenie: KLIMTECH_LAYOUT_MODEL=layoutlmv3 (wymaga GPU)
# ---------------------------------------------------------------------------

_HEADER_THRESHOLD = 0.12   # górne 12% strony = nagłówek
_FOOTER_THRESHOLD = 0.88   # dolne 12% strony = stopka
_MIN_TEXT_LEN = 10          # minimum znaków aby region był treścią


@dataclass
class PageRegion:
    """Pojedynczy region na stronie PDF."""

    page_num: int
    region_type: str        # text | header | footer | image | table_hint
    content: str = ""       # tekst (pusty dla image)
    bbox: tuple = field(default_factory=tuple)  # (x0, y0, x1, y1) znormalizowane 0..1
    confidence: float = 1.0


def _classify_block(block: dict, page_height: float) -> str:
    """Klasyfikuje blok PyMuPDF na podstawie pozycji i typu."""
    block_type = block.get("type", 0)  # 0=tekst, 1=obraz

    if block_type == 1:
        return "image"

    # Znormalizowana pozycja pionowa
    y0_norm = block["bbox"][1] / page_height if page_height > 0 else 0.5
    y1_norm = block["bbox"][3] / page_height if page_height > 0 else 0.5

    # Heurystyka nagłówek/stopka na podstawie pozycji
    if y1_norm < _HEADER_THRESHOLD:
        return "header"
    if y0_norm > _FOOTER_THRESHOLD:
        return "footer"

    # Sprawdź czy to hint na tabelę (linie poziome w tekście)
    lines = block.get("lines", [])
    if len(lines) > 1:
        # Tabele często mają wiele krótkich linii z podobną strukturą
        line_texts = []
        for ln in lines[:5]:
            spans = ln.get("spans", [])
            line_texts.append("".join(s.get("text", "") for s in spans))
        # Heurystyka: jeśli > 3 linie z separatorami "|" lub "\t" → table_hint
        sep_count = sum(1 for t in line_texts if "|" in t or "\t" in t)
        if sep_count >= 2:
            return "table_hint"

    return "text"


def parse_pdf_layout(pdf_path: str) -> List[PageRegion]:
    """Parsuje PDF i zwraca sklasyfikowane regiony stron.

    Używa PyMuPDF (fitz). Przy braku fitz — zwraca pusty list z logiem.
    """
    try:
        import fitz
    except ImportError:
        logger.debug("[Layout] PyMuPDF niedostępne — layout analysis pominięty")
        return []

    regions: List[PageRegion] = []
    try:
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc, start=1):
            page_height = page.rect.height or 1.0
            page_width = page.rect.width or 1.0
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get(
                "blocks", []
            )

            for block in blocks:
                region_type = _classify_block(block, page_height)

                if region_type == "image":
                    bbox = block.get("bbox", (0, 0, 0, 0))
                    regions.append(
                        PageRegion(
                            page_num=page_num,
                            region_type="image",
                            content="",
                            bbox=(
                                bbox[0] / page_width,
                                bbox[1] / page_height,
                                bbox[2] / page_width,
                                bbox[3] / page_height,
                            ),
                        )
                    )
                    continue

                # Zbierz tekst z bloków tekstowych
                text_parts = []
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text_parts.append(span.get("text", ""))
                content = " ".join(text_parts).strip()

                if len(content) < _MIN_TEXT_LEN and region_type == "text":
                    continue

                bbox = block.get("bbox", (0, 0, 0, 0))
                regions.append(
                    PageRegion(
                        page_num=page_num,
                        region_type=region_type,
                        content=content,
                        bbox=(
                            bbox[0] / page_width,
                            bbox[1] / page_height,
                            bbox[2] / page_width,
                            bbox[3] / page_height,
                        ),
                    )
                )

        doc.close()
        stats = {
            "text": sum(1 for r in regions if r.region_type == "text"),
            "header": sum(1 for r in regions if r.region_type == "header"),
            "footer": sum(1 for r in regions if r.region_type == "footer"),
            "image": sum(1 for r in regions if r.region_type == "image"),
            "table_hint": sum(1 for r in regions if r.region_type == "table_hint"),
        }
        logger.info(
            "[Layout] %s — %d stron, regiony: %s",
            pdf_path.split("/")[-1],
            len(doc) if not doc.is_closed else "?",
            stats,
        )
    except Exception as e:
        logger.warning("[Layout] Błąd analizy układu: %s", e)

    return regions


def regions_to_text_chunks(regions: List[PageRegion]) -> str:
    """Łączy regiony tekstowe w jedną treść, pomijając nagłówki i stopki.

    Tabele (table_hint) są oznaczone separatorem dla chunking.
    """
    parts: List[str] = []
    for region in regions:
        if region.region_type in ("header", "footer", "image"):
            continue  # nagłówki/stopki/obrazy nie wchodzą do treści
        if region.region_type == "table_hint":
            parts.append(f"\n[TABELA]\n{region.content}\n[/TABELA]\n")
        else:
            parts.append(region.content)

    return "\n\n".join(p for p in parts if p.strip())


def get_image_regions(regions: List[PageRegion]) -> List[PageRegion]:
    """Zwraca tylko regiony obrazów (dla VLM pipeline)."""
    return [r for r in regions if r.region_type == "image"]


def get_layout_summary(regions: List[PageRegion]) -> dict:
    """Zwraca statystyki układu dokumentu — przydatne w meta."""
    return {
        "layout_text_blocks": sum(1 for r in regions if r.region_type == "text"),
        "layout_images": sum(1 for r in regions if r.region_type == "image"),
        "layout_tables": sum(1 for r in regions if r.region_type == "table_hint"),
        "layout_headers_stripped": sum(
            1 for r in regions if r.region_type in ("header", "footer")
        ),
    }
