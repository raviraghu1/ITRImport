#!/usr/bin/env python3
"""
PDF Content Extractor using PyMuPDF (fitz)
Extracts text content from PDF files and saves to text/JSON format.
"""

import fitz  # PyMuPDF
import json
import sys
from pathlib import Path


def extract_pdf_to_text(pdf_path: str, output_txt: str = None, output_json: str = None):
    """
    Extract text content from a PDF file.

    Args:
        pdf_path: Path to the PDF file
        output_txt: Optional path for text output
        output_json: Optional path for JSON output

    Returns:
        dict containing extracted content
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)

    result = {
        "source_file": str(pdf_path),
        "total_pages": len(doc),
        "metadata": dict(doc.metadata) if doc.metadata else {},
        "pages": []
    }

    full_text = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        result["pages"].append({
            "page_number": page_num,
            "text": text
        })
        full_text.append(f"--- Page {page_num} ---\n{text}")

    doc.close()

    # Save to text file
    if output_txt:
        output_txt = Path(output_txt)
        output_txt.parent.mkdir(parents=True, exist_ok=True)
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(f"Source: {pdf_path}\n")
            f.write(f"Total Pages: {result['total_pages']}\n")
            f.write("=" * 80 + "\n\n")
            f.write("\n\n".join(full_text))
        print(f"Text output saved to: {output_txt}")

    # Save to JSON file
    if output_json:
        output_json = Path(output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"JSON output saved to: {output_json}")

    return result


if __name__ == "__main__":
    # Default paths
    pdf_file = "Files/TR Complete March 2024.pdf"
    txt_output = "Files/TR_Complete_March_2024.txt"
    json_output = "Files/TR_Complete_March_2024.json"

    # Allow command line override
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
    if len(sys.argv) > 2:
        txt_output = sys.argv[2]
    if len(sys.argv) > 3:
        json_output = sys.argv[3]

    print(f"Extracting content from: {pdf_file}")
    result = extract_pdf_to_text(pdf_file, txt_output, json_output)
    print(f"\nExtraction complete!")
    print(f"Total pages extracted: {result['total_pages']}")

    # Print first 500 chars as preview
    if result["pages"]:
        preview = result["pages"][0]["text"][:500]
        print(f"\nPreview of first page:\n{'-' * 40}\n{preview}...")
