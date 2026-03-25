#!/usr/bin/env python3
"""Skrypt do indeksowania PDF do RAG - z podziałem na strony i resume."""

import os
import sys
import time
import json
from pathlib import Path

_SCRIPT_BASE = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, _SCRIPT_BASE)

import fitz  # PyMuPDF
from haystack import Pipeline, Document
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack.utils import ComponentDevice
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat

PDF_DIR = os.path.join(_SCRIPT_BASE, "data", "uploads", "pdf_RAG")
PAGES_DIR = os.path.join(_SCRIPT_BASE, "data", "uploads", "pdf_pages")
PROGRESS_FILE = os.path.join(_SCRIPT_BASE, "data", "uploads", "pdf_progress.json")

os.makedirs(PAGES_DIR, exist_ok=True)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def split_pdf_to_pages(pdf_path):
    """Dzieli PDF na pojedyncze strony."""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    pages_subdir = os.path.join(PAGES_DIR, pdf_name)
    os.makedirs(pages_subdir, exist_ok=True)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"  📄 PDF ma {total_pages} stron")

    existing = len([f for f in os.listdir(pages_subdir) if f.endswith(".pdf")])
    if existing == total_pages:
        print(f"  ✓ Strony już podzielone ({existing} plików)")
        doc.close()
        return pages_subdir, total_pages

    print(f"  🔪 Dzielę na strony...")
    for i, page in enumerate(doc):
        single_page = fitz.open()
        single_page.insert_pdf(doc, from_page=i, to_page=i)
        page_path = os.path.join(pages_subdir, f"page_{i + 1:04d}.pdf")
        single_page.save(page_path)
        single_page.close()
        if (i + 1) % 10 == 0:
            print(f"    → {i + 1}/{total_pages}")

    doc.close()
    print(f"  ✅ Podzielono na {total_pages} plików")
    return pages_subdir, total_pages


def ocr_page(page_path, converter):
    """OCR pojedynczej strony."""
    result = converter.convert(page_path)
    return result.document.export_to_markdown()


def main():
    print("=" * 60)
    print("  RAG PDF Ingest (GPU) - z resume")
    print("=" * 60)

    doc_store = QdrantDocumentStore(
        url="http://localhost:6333",
        index="klimtech_docs",
        embedding_dim=1024,
        recreate_index=False,
    )

    indexing_pipeline = Pipeline()
    indexing_pipeline.add_component(
        "splitter",
        DocumentSplitter(split_by="word", split_length=200, split_overlap=30),
    )
    indexing_pipeline.add_component(
        "embedder",
        SentenceTransformersDocumentEmbedder(
            model="intfloat/multilingual-e5-large",
            device=ComponentDevice.from_str("cuda:0"),
        ),
    )
    indexing_pipeline.add_component(
        "writer",
        DocumentWriter(document_store=doc_store, policy=DuplicatePolicy.OVERWRITE),
    )
    indexing_pipeline.connect("splitter", "embedder")
    indexing_pipeline.connect("embedder", "writer")

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
    print(f"\n📁 Znaleziono {len(pdf_files)} plików PDF")

    progress = load_progress()

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = EasyOcrOptions(lang=["pl", "en"], use_gpu=True)
    pipeline_options.ocr_options.force_full_page_ocr = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        file_size_mb = os.path.getsize(pdf_path) / 1024 / 1024

        print(f"\n{'=' * 60}")
        print(f"📖 {pdf_file} ({file_size_mb:.1f} MB)")

        pdf_key = os.path.basename(pdf_path)
        if pdf_key not in progress:
            progress[pdf_key] = {"total": 0, "done": [], "chunks": 0}

        pages_dir, total_pages = split_pdf_to_pages(pdf_path)
        progress[pdf_key]["total"] = total_pages
        save_progress(progress)

        all_text = []
        start_from = len(progress[pdf_key]["done"])
        if start_from > 0:
            print(f"  ⏩ Wznawiam od strony {start_from + 1}")

        page_files = sorted([f for f in os.listdir(pages_dir) if f.endswith(".pdf")])
        overall_start = time.time()

        for i, page_file in enumerate(page_files):
            page_num = i + 1
            if page_num <= start_from:
                continue

            page_path = os.path.join(pages_dir, page_file)
            page_start = time.time()

            try:
                print(f"  📄 Strona {page_num}/{total_pages}...", end=" ", flush=True)
                markdown = ocr_page(page_path, converter)

                elapsed = time.time() - page_start
                chars = len(markdown)

                if chars > 50:
                    all_text.append(f"\n--- STRONA {page_num} ---\n{markdown}")
                    print(f"✓ {chars} znaków ({elapsed:.1f}s)")
                else:
                    print(f"⚠ pusta ({elapsed:.1f}s)")

                progress[pdf_key]["done"].append(page_num)
                save_progress(progress)

            except Exception as e:
                print(f"❌ Błąd: {e}")
                progress[pdf_key]["done"].append(page_num)
                save_progress(progress)
                continue

        if all_text:
            full_text = "\n".join(all_text)
            print(f"\n  📊 Łącznie {len(full_text)} znaków")
            print("  🔍 Indeksowanie...")

            docs = [
                Document(content=full_text, meta={"source": pdf_file, "type": ".pdf"})
            ]
            result = indexing_pipeline.run({"splitter": {"documents": docs}})
            chunks = result["writer"]["documents_written"]
            progress[pdf_key]["chunks"] = chunks
            save_progress(progress)

            total_time = time.time() - overall_start
            print(f"  ✅ Zaindeksowano {chunks} chunków w {total_time:.1f}s")

    print("\n" + "=" * 60)
    print("🎉 Zakończono!")
    print("=" * 60)


if __name__ == "__main__":
    main()
