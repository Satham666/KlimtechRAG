#!/usr/bin/env python3
"""Skrypt do ręcznego indeksowania plików PDF do bazy RAG."""

import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/KlimtechRAG"))

from haystack import Pipeline, Document
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack.utils import ComponentDevice
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from docling.document_converter import DocumentConverter

PDF_DIR = "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/pdf_RAG"

print("=" * 50)
print("  RAG PDF Ingest Script")
print("=" * 50)

doc_store = QdrantDocumentStore(
    url="http://localhost:6333",
    index="klimtech_docs",
    embedding_dim=1024,
    recreate_index=False,
)

indexing_pipeline = Pipeline()
indexing_pipeline.add_component(
    "splitter", DocumentSplitter(split_by="word", split_length=200, split_overlap=30)
)
indexing_pipeline.add_component(
    "embedder",
    SentenceTransformersDocumentEmbedder(
        model="intfloat/multilingual-e5-large", device=ComponentDevice.from_str("cpu")
    ),
)
indexing_pipeline.add_component(
    "writer", DocumentWriter(document_store=doc_store, policy=DuplicatePolicy.OVERWRITE)
)
indexing_pipeline.connect("splitter", "embedder")
indexing_pipeline.connect("embedder", "writer")

pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
print(f"\nZnaleziono {len(pdf_files)} plików PDF:")
for f in pdf_files:
    print(f"  - {f}")

print("\nRozpoczynam indeksowanie...\n")

for pdf_file in pdf_files:
    pdf_path = os.path.join(PDF_DIR, pdf_file)
    file_size_mb = os.path.getsize(pdf_path) / 1024 / 1024

    print(f"\n{'=' * 50}")
    print(f"Przetwarzam: {pdf_file} ({file_size_mb:.1f} MB)")

    start_time = time.time()

    try:
        print("  1. Parsowanie PDF (Docling)...")
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        markdown = result.document.export_to_markdown()
        print(f"     Wyodrębniono {len(markdown)} znaków")

        if len(markdown) < 100:
            print("     ⚠️ Za mało treści, pomijam.")
            continue

        print("  2. Splitting i embedding...")
        docs = [Document(content=markdown, meta={"source": pdf_file, "type": ".pdf"})]

        result = indexing_pipeline.run({"splitter": {"documents": docs}})
        chunks = result["writer"]["documents_written"]

        elapsed = time.time() - start_time
        print(f"  ✅ Zaindeksowano {chunks} chunków w {elapsed:.1f}s")

    except Exception as e:
        print(f"  ❌ Błąd: {e}")

print("\n" + "=" * 50)
print("Zakończono indeksowanie.")
print("=" * 50)
