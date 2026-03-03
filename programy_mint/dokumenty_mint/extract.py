#!/usr/bin/env python3
import sys
import pypdf

def extract_text(pdf_path):
    with open(pdf_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                print(f"--- Strona {i + 1} ---")
                print(text)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Użycie: python3 extract.py plik.pdf")
        sys.exit(1)

    extract_text(sys.argv[1])
