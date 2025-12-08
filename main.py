#!/usr/bin/env python3
"""
ITRImport - ITR Economics Data Extraction and Analysis

Main entry point for extracting economic data from ITR Trends Report PDFs,
storing in MongoDB, and generating analysis reports.

Usage:
    python main.py                          # Process all PDFs in Files/
    python main.py --pdf "path/to/file.pdf" # Process single PDF
    python main.py --analyze                # Analyze existing data
    python main.py --export                 # Export to CSV/JSON
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.parser import ITRParser
from src.database import ITRDatabase
from src.analyzer import ITRAnalyzer
from src.models import Sector


def get_mongodb_uri() -> str:
    """Get MongoDB connection URI from environment variable."""
    uri = os.getenv("ITR_MONGODB_URI")
    if not uri:
        print("Warning: ITR_MONGODB_URI not set. Using localhost.")
        return "mongodb://localhost:27017"
    return uri


def process_pdf(pdf_path: Path, db: ITRDatabase, verbose: bool = True) -> dict:
    """
    Process a single PDF file.

    Args:
        pdf_path: Path to the PDF file
        db: Database connection
        verbose: Print progress messages

    Returns:
        Processing statistics
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'='*60}")

    stats = {
        "pdf": pdf_path.name,
        "series_extracted": 0,
        "series_inserted": 0,
        "series_updated": 0,
        "errors": []
    }

    try:
        with ITRParser(pdf_path) as parser:
            if verbose:
                print(f"Report Period: {parser.report_period}")
                print(f"Total Pages: {parser.get_page_count()}")

            # Extract all series
            series_list = parser.extract_all_series()
            stats["series_extracted"] = len(series_list)

            if verbose:
                print(f"Series Extracted: {len(series_list)}")

            # Store in database
            if db.db is not None:
                result = db.upsert_many_series(series_list)
                stats["series_inserted"] = result["inserted"]
                stats["series_updated"] = result["updated"]

                # Save report metadata
                db.save_report_metadata(parser.get_report_metadata())

                if verbose:
                    print(f"Database: {result['inserted']} inserted, {result['updated']} updated")

            # Generate analysis
            analyzer = ITRAnalyzer(series_list)

            if verbose:
                print("\nSeries by Sector:")
                for sector, count in analyzer.count_by_sector().items():
                    if count > 0:
                        print(f"  {sector}: {count}")

            # Export reports
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)

            report_name = pdf_path.stem.replace(" ", "_")

            # Text report
            report_path = output_dir / f"{report_name}_report.txt"
            analyzer.generate_report(report_path)

            # JSON export
            json_path = output_dir / f"{report_name}_data.json"
            analyzer.export_to_json(json_path)

            # CSV export
            csv_path = output_dir / f"{report_name}_summary.csv"
            analyzer.export_to_csv(csv_path)

    except Exception as e:
        stats["errors"].append(str(e))
        if verbose:
            print(f"ERROR: {e}")

    return stats


def find_pdf_files(directory: Path) -> list[Path]:
    """Find all PDF files in a directory."""
    return sorted(directory.glob("*.pdf"))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ITR Economics Data Extraction and Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                              # Process all PDFs in Files/
    python main.py --pdf Files/report.pdf       # Process single PDF
    python main.py --no-db                      # Process without MongoDB
    python main.py --stats                      # Show database statistics
        """
    )

    parser.add_argument(
        "--pdf",
        type=Path,
        help="Process a specific PDF file"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("Files"),
        help="Directory containing PDF files (default: Files/)"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip database operations (extraction only)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics and exit"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )

    args = parser.parse_args()
    verbose = not args.quiet

    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                     ITRImport v1.0.0                        ║
    ║         ITR Economics Data Extraction & Analysis            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    # Initialize database connection
    db = ITRDatabase(get_mongodb_uri())

    if not args.no_db:
        try:
            db.connect()
        except Exception as e:
            print(f"Warning: Could not connect to MongoDB: {e}")
            print("Continuing without database storage...")
            args.no_db = True

    # Show stats and exit
    if args.stats:
        if args.no_db:
            print("Cannot show stats without database connection.")
            return 1

        stats = db.get_stats()
        print("\nDatabase Statistics:")
        print(f"  Database: {stats['database']}")
        print("\n  Collections:")
        for name, info in stats.get("collections", {}).items():
            print(f"    {name}: {info['count']} documents")
        db.close()
        return 0

    # Determine which PDFs to process
    if args.pdf:
        if not args.pdf.exists():
            print(f"Error: PDF file not found: {args.pdf}")
            return 1
        pdf_files = [args.pdf]
    else:
        pdf_files = find_pdf_files(args.dir)
        if not pdf_files:
            print(f"No PDF files found in: {args.dir}")
            return 1

    print(f"Found {len(pdf_files)} PDF file(s) to process")

    # Process each PDF
    all_stats = []
    for pdf_path in pdf_files:
        stats = process_pdf(pdf_path, db, verbose)
        all_stats.append(stats)

    # Summary
    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE")
    print(f"{'='*60}")

    total_extracted = sum(s["series_extracted"] for s in all_stats)
    total_inserted = sum(s["series_inserted"] for s in all_stats)
    total_updated = sum(s["series_updated"] for s in all_stats)
    total_errors = sum(len(s["errors"]) for s in all_stats)

    print(f"PDFs Processed: {len(all_stats)}")
    print(f"Total Series Extracted: {total_extracted}")

    if not args.no_db:
        print(f"Database Inserts: {total_inserted}")
        print(f"Database Updates: {total_updated}")

    if total_errors > 0:
        print(f"Errors: {total_errors}")
        for stats in all_stats:
            for error in stats["errors"]:
                print(f"  - {stats['pdf']}: {error}")

    print(f"\nOutput files saved to: {Path('output').absolute()}")

    # Cleanup
    if not args.no_db:
        db.close()

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
