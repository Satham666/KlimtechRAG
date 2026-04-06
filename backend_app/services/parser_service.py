import logging
import re
import subprocess

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Parser Service — ekstrakcja tekstu z PDF, DOCX, TXT i innych formatów
# Wydzielony z routes/ingest.py (A1b refaktoryzacja)
# ---------------------------------------------------------------------------


def clean_text(text: str) -> str:
    """Normalizuje whitespace i usuwa puste linie."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def extract_pdf_text(file_path: str) -> str:
    """Próbuje wyekstrahować tekst z PDF przez pdftotext (szybka ścieżka).

    Zwraca pusty string jeśli pdftotext niedostępny lub PDF jest skanowany.
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", file_path, "-"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        text = result.stdout.strip()
        if len(text) > 100:
            return text
    except subprocess.TimeoutExpired:
        logger.warning("[PDF] pdftotext timeout po 30s dla: %s", file_path)
    except Exception as e:
        logger.warning("[PDF] pdftotext błąd: %s", e)
    return ""


def _fallback_docling_ocr(file_path: str) -> str:
    """Docling OCR fallback gdy pdftotext zwraca pusty tekst."""
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter

    logger.info("[PDF] pdftotext pusty → Docling OCR...")
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = RapidOcrOptions(
        lang=["english", "polish"],
        force_full_page_ocr=True,
        bitmap_area_threshold=0.0,
        backend="onnxruntime",
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    result = converter.convert(file_path)
    return result.document.export_to_markdown()


def parse_with_docling(file_path: str) -> str:
    """Parsuje PDF: najpierw pdftotext z layout analysis, fallback na Docling OCR.

    Zwraca oczyszczony tekst w formacie markdown.
    C1: Gdy PyMuPDF dostępny — filtruje nagłówki/stopki i oznacza tabele.
    """
    # C1: Layout analysis — filtrowanie nagłówków/stopek/tabel przez PyMuPDF
    from .layout_service import get_layout_summary, parse_pdf_layout, regions_to_text_chunks

    regions = parse_pdf_layout(file_path)
    layout_result = ""
    if regions:
        layout_text = regions_to_text_chunks(regions)
        if layout_text and len(layout_text) > 100:
            summary = get_layout_summary(regions)
            logger.info("[PDF] Layout analysis OK: %s", summary)
            layout_result = clean_text(layout_text)
        else:
            logger.debug("[PDF] Layout analysis zwróciło za mało tekstu — fallback pdftotext")

    text = layout_result or extract_pdf_text(file_path)
    if not text:
        text = _fallback_docling_ocr(file_path)

    # C3: Table Structure Recognition — dolacz tabele jako Markdown
    from .table_service import extract_tables_as_text
    tables_md = extract_tables_as_text(file_path)
    if tables_md:
        text = text + tables_md

    return clean_text(text)


def read_text_file(file_path: str, suffix: str) -> str:
    """Odczytuje pliki tekstowe / docx / odt.

    Dla .doc/.docx/.odt/.rtf używa mammoth. Fallback na zwykły odczyt UTF-8.
    """
    if suffix in {".doc", ".docx", ".odt", ".rtf"}:
        try:
            import mammoth

            with open(file_path, "rb") as f:
                result = mammoth.extract_raw_text(f)
            return clean_text(result.value)
        except Exception as e:
            logger.warning("[TEXT] mammoth nie powiódł się (%s), czytam jako tekst", e)
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return clean_text(f.read())
