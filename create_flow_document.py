#!/usr/bin/env python3
"""
Create Flow-Based Consolidated Documents for ITR Economics Reports.

This script creates documents that maintain the natural flow of the PDF,
preserving context between text, charts, and images. Uses LLM for
interpretations of visual content.

Stores documents in 'ITRextract_Flow' collection.

Usage:
    python create_flow_document.py                           # Process all PDFs
    python create_flow_document.py --pdf "Files/report.pdf"  # Single PDF
    python create_flow_document.py --no-llm                  # Skip LLM interpretations
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.flow_extractor import FlowExtractor, create_flow_document
from src.llm_extractor import LLMExtractor

# MongoDB configuration
MONGODB_URI = os.getenv("ITR_MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("ITR_DATABASE_NAME", "ITRReports")
COLLECTION_NAME = "ITRextract_Flow"


def connect_to_mongodb():
    """Connect to MongoDB."""
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    print(f"Connected to MongoDB: {DATABASE_NAME}")
    return client, db


def setup_collection(db):
    """Set up the ITRextract_Flow collection with indexes."""
    coll = db[COLLECTION_NAME]

    # Create indexes
    coll.create_index([("report_id", ASCENDING)], unique=True, name="report_id_idx")
    coll.create_index([("report_period", ASCENDING)], name="period_idx")
    coll.create_index([("pdf_filename", ASCENDING)], name="filename_idx")
    coll.create_index([("series_index", ASCENDING)], name="series_idx")

    print(f"Collection '{COLLECTION_NAME}' ready with indexes")
    return coll


def process_pdf(pdf_path: Path, llm, db, verbose: bool = True) -> dict:
    """Process a single PDF into a flow document."""
    if verbose:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'='*60}")

    stats = {
        "pdf": pdf_path.name,
        "success": False,
        "pages": 0,
        "series": 0,
        "charts": 0,
        "llm_interpretations": 0,
        "error": None
    }

    try:
        # Create the flow document
        with FlowExtractor(pdf_path, llm) as extractor:
            document = extractor.extract_full_document_flow()

        stats["pages"] = document["metadata"]["total_pages"]
        stats["series"] = len(document["series_index"])
        stats["charts"] = document["metadata"]["total_charts"]

        # Count LLM interpretations
        for page in document["document_flow"]:
            for block in page.get("blocks", []):
                if block.get("interpretation"):
                    stats["llm_interpretations"] += 1

        if verbose:
            print(f"  Report Period: {document['report_period']}")
            print(f"  Pages: {stats['pages']}")
            print(f"  Series: {stats['series']}")
            print(f"  Charts: {stats['charts']}")
            print(f"  LLM Interpretations: {stats['llm_interpretations']}")

        # Store in MongoDB
        if db is not None:
            coll = db[COLLECTION_NAME]
            result = coll.update_one(
                {"report_id": document["report_id"]},
                {"$set": document},
                upsert=True
            )

            if result.upserted_id:
                if verbose:
                    print(f"  MongoDB: CREATED")
            else:
                if verbose:
                    print(f"  MongoDB: UPDATED")

        # Also save to JSON file
        output_dir = Path("output/flow")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{document['report_id']}_flow.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(document, f, indent=2, ensure_ascii=False, default=str)

        if verbose:
            print(f"  Saved: {output_file.name}")

        stats["success"] = True

    except Exception as e:
        stats["error"] = str(e)
        if verbose:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Create flow-based consolidated documents for ITR Economics reports",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--pdf", type=Path, help="Process a specific PDF file")
    parser.add_argument("--dir", type=Path, default=Path("Files"),
                       help="Directory containing PDF files")
    parser.add_argument("--no-llm", action="store_true",
                       help="Skip LLM interpretations")
    parser.add_argument("--no-db", action="store_true",
                       help="Skip MongoDB storage")
    parser.add_argument("--quiet", action="store_true",
                       help="Suppress verbose output")

    args = parser.parse_args()
    verbose = not args.quiet

    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║       ITR Flow Document Creator v1.0.0                      ║
    ║    Maintaining PDF Context for Better LLM Understanding      ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    # Initialize LLM
    llm = None
    if not args.no_llm:
        try:
            llm = LLMExtractor()
            print("LLM Extractor initialized (Azure OpenAI GPT-4)")
        except Exception as e:
            print(f"Warning: LLM initialization failed: {e}")
            print("Continuing without LLM interpretations...")

    # Connect to MongoDB
    db = None
    if not args.no_db:
        try:
            client, db = connect_to_mongodb()
            setup_collection(db)
        except Exception as e:
            print(f"Warning: MongoDB connection failed: {e}")
            print("Continuing without database storage...")

    # Find PDFs to process
    if args.pdf:
        if not args.pdf.exists():
            print(f"Error: PDF not found: {args.pdf}")
            return 1
        pdf_files = [args.pdf]
    else:
        pdf_files = sorted(args.dir.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in: {args.dir}")
            return 1

    print(f"\nFound {len(pdf_files)} PDF file(s) to process")

    # Process each PDF
    all_stats = []
    for pdf_path in pdf_files:
        stats = process_pdf(pdf_path, llm, db, verbose)
        all_stats.append(stats)

    # Summary
    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE")
    print(f"{'='*60}")

    successful = sum(1 for s in all_stats if s["success"])
    failed = len(all_stats) - successful
    total_pages = sum(s["pages"] for s in all_stats)
    total_series = sum(s["series"] for s in all_stats)
    total_charts = sum(s["charts"] for s in all_stats)
    total_interpretations = sum(s["llm_interpretations"] for s in all_stats)

    print(f"\nPDFs Processed: {len(all_stats)} ({successful} successful, {failed} failed)")
    print(f"Total Pages: {total_pages}")
    print(f"Total Series: {total_series}")
    print(f"Total Charts: {total_charts}")
    print(f"LLM Interpretations: {total_interpretations}")
    print(f"\nCollection: {COLLECTION_NAME}")
    print(f"Output: output/flow/")

    if failed > 0:
        print(f"\nFailed PDFs:")
        for s in all_stats:
            if not s["success"]:
                print(f"  - {s['pdf']}: {s['error']}")

    # Cleanup
    if llm:
        llm.close()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
