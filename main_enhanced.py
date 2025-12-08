#!/usr/bin/env python3
"""
ITRImport Enhanced - ITR Economics Data Extraction with LLM Support

Enhanced extraction using GPT-4 for intelligent parsing of charts,
tables, and economic context from ITR Trends Report PDFs.

Usage:
    python main_enhanced.py                          # Process all PDFs
    python main_enhanced.py --pdf "path/to/file.pdf" # Process single PDF
    python main_enhanced.py --no-llm                 # Skip LLM extraction
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.enhanced_parser import EnhancedITRParser
from src.enhanced_analyzer import EnhancedITRAnalyzer
from src.llm_extractor import LLMExtractor
from src.database import ITRDatabase
from src.models import Sector


def get_mongodb_uri() -> str:
    """Get MongoDB connection URI from environment variable."""
    uri = os.getenv("ITR_MONGODB_URI")
    if not uri:
        print("Warning: ITR_MONGODB_URI not set. Using localhost.")
        return "mongodb://localhost:27017"
    return uri


def process_pdf_enhanced(
    pdf_path: Path,
    db: ITRDatabase,
    llm: LLMExtractor = None,
    verbose: bool = True
) -> dict:
    """Process a single PDF with enhanced extraction."""

    if verbose:
        print(f"\n{'='*70}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'='*70}")

    stats = {
        "pdf": pdf_path.name,
        "series_extracted": 0,
        "charts_found": 0,
        "forecast_tables": 0,
        "llm_enhanced": 0,
        "errors": []
    }

    try:
        with EnhancedITRParser(pdf_path) as parser:
            if verbose:
                print(f"Report Period: {parser.report_period}")
                print(f"Total Pages: {parser.get_page_count()}")

            # Get report metadata
            report_metadata = parser.get_report_metadata()

            # Extract all series with enhanced parsing
            series_list = parser.extract_all_series()
            stats["series_extracted"] = len(series_list)

            # Count charts and tables
            for series in series_list:
                stats["charts_found"] += len(series.charts)
                if series.forecast_table:
                    stats["forecast_tables"] += 1

            if verbose:
                print(f"Series Extracted: {len(series_list)}")
                print(f"Charts Found: {stats['charts_found']}")
                print(f"Forecast Tables: {stats['forecast_tables']}")

            # LLM Enhancement
            if llm:
                if verbose:
                    print("\nEnhancing with LLM...")

                for series in series_list:
                    try:
                        # Get page text for this series
                        page_num = series.source.page_number - 1 if series.source else 0
                        page = parser.doc[page_num]
                        page_text = page.get_text()

                        # Use LLM to extract/enhance data
                        llm_data = llm.extract_series_data(page_text, series.series_name)

                        if llm_data:
                            # Merge LLM data with parsed data
                            if not series.highlights and llm_data.get('highlights'):
                                series.highlights = llm_data['highlights']

                            if not series.management_objective and llm_data.get('management_objective'):
                                series.management_objective = llm_data['management_objective']

                            if not series.overview_text and llm_data.get('overview'):
                                series.overview_text = llm_data['overview']

                            # Enhanced forecast extraction
                            if llm_data.get('forecasts') and len(llm_data['forecasts']) > len(series.forecasts):
                                from src.models import ForecastRange
                                for f in llm_data['forecasts']:
                                    if isinstance(f, dict) and f.get('year'):
                                        series.forecasts.append(ForecastRange(
                                            year=f['year'],
                                            metric_type="12/12",
                                            value_point=f.get('rate_12_12')
                                        ))
                                        if f.get('value_12mma'):
                                            series.forecasts.append(ForecastRange(
                                                year=f['year'],
                                                metric_type="12MMA",
                                                value_point=f.get('value_12mma')
                                            ))

                            stats["llm_enhanced"] += 1

                    except Exception as e:
                        if verbose:
                            print(f"  LLM error for {series.series_name}: {e}")

                if verbose:
                    print(f"LLM Enhanced: {stats['llm_enhanced']} series")

                # Extract executive summary with LLM
                exec_text = ""
                for page_num in range(min(10, parser.get_page_count())):
                    page_text = parser.doc[page_num].get_text()
                    if "Executive Summary" in page_text:
                        exec_text = page_text
                        break

                if exec_text:
                    exec_summary = llm.extract_executive_summary(exec_text)
                    if exec_summary:
                        report_metadata['executive_summary_enhanced'] = exec_summary

            # Generate analysis
            analyzer = EnhancedITRAnalyzer(series_list, report_metadata)

            if verbose:
                print("\nSeries by Sector:")
                for sector, count in analyzer.count_by_sector().items():
                    if count > 0:
                        print(f"  {sector}: {count}")

            # Create output directory
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)

            report_name = pdf_path.stem.replace(" ", "_")

            # Generate detailed report
            report_path = output_dir / f"{report_name}_enhanced_report.txt"
            analyzer.generate_detailed_report(report_path)

            # JSON export
            json_path = output_dir / f"{report_name}_enhanced_data.json"
            analyzer.export_to_json(json_path)

            # CSV export
            csv_path = output_dir / f"{report_name}_enhanced_summary.csv"
            analyzer.export_to_csv(csv_path)

            # Charts manifest
            charts_path = output_dir / f"{report_name}_charts_manifest.json"
            analyzer.export_charts_manifest(charts_path)

            # Forecast tables
            tables_path = output_dir / f"{report_name}_forecast_tables.json"
            analyzer.export_forecast_tables(tables_path)

            # Store in database if connected
            if db.db is not None:
                # Convert to basic EconomicSeries for database storage
                from src.models import EconomicSeries, ForecastRange
                for series in series_list:
                    basic_series = EconomicSeries(
                        series_id=series.series_id,
                        series_name=series.series_name,
                        sector=series.sector,
                        unit=series.unit,
                        current_value=series.current_value,
                        current_period=series.current_period,
                        rate_12_12=series.rate_12_12,
                        current_phase=series.current_phase,
                        forecasts=[ForecastRange(
                            year=f.year,
                            metric_type=f.metric_type,
                            value_point=f.value_point
                        ) for f in series.forecasts],
                        highlights=series.highlights,
                        management_objective=series.management_objective,
                        source=series.source
                    )
                    db.upsert_series(basic_series)

                db.save_report_metadata(report_metadata)
                if verbose:
                    print(f"\nStored {len(series_list)} series in MongoDB")

    except Exception as e:
        stats["errors"].append(str(e))
        if verbose:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

    return stats


def find_pdf_files(directory: Path) -> list[Path]:
    """Find all PDF files in a directory."""
    return sorted(directory.glob("*.pdf"))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ITR Economics Enhanced Data Extraction with LLM Support",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--pdf", type=Path, help="Process a specific PDF file")
    parser.add_argument("--dir", type=Path, default=Path("Files"),
                       help="Directory containing PDF files")
    parser.add_argument("--no-db", action="store_true",
                       help="Skip database operations")
    parser.add_argument("--no-llm", action="store_true",
                       help="Skip LLM-enhanced extraction")
    parser.add_argument("--stats", action="store_true",
                       help="Show database statistics and exit")
    parser.add_argument("--quiet", action="store_true",
                       help="Suppress verbose output")

    args = parser.parse_args()
    verbose = not args.quiet

    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                  ITRImport Enhanced v2.0.0                      ║
    ║       ITR Economics Data Extraction with LLM Support            ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    # Initialize database
    db = ITRDatabase(get_mongodb_uri())
    if not args.no_db:
        try:
            db.connect()
        except Exception as e:
            print(f"Warning: Could not connect to MongoDB: {e}")
            args.no_db = True

    # Show stats and exit
    if args.stats:
        if args.no_db:
            print("Cannot show stats without database connection.")
            return 1
        stats = db.get_stats()
        print("\nDatabase Statistics:")
        print(f"  Database: {stats['database']}")
        for name, info in stats.get("collections", {}).items():
            print(f"    {name}: {info['count']} documents")
        db.close()
        return 0

    # Initialize LLM extractor
    llm = None
    if not args.no_llm:
        try:
            llm = LLMExtractor()
            print("LLM Extractor initialized (Azure OpenAI GPT-4)")
        except Exception as e:
            print(f"Warning: Could not initialize LLM: {e}")
            print("Continuing without LLM enhancement...")

    # Find PDFs to process
    if args.pdf:
        if not args.pdf.exists():
            print(f"Error: PDF not found: {args.pdf}")
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
        stats = process_pdf_enhanced(pdf_path, db, llm, verbose)
        all_stats.append(stats)

    # Summary
    print(f"\n{'='*70}")
    print("PROCESSING COMPLETE")
    print(f"{'='*70}")

    total_series = sum(s["series_extracted"] for s in all_stats)
    total_charts = sum(s["charts_found"] for s in all_stats)
    total_tables = sum(s["forecast_tables"] for s in all_stats)
    total_llm = sum(s["llm_enhanced"] for s in all_stats)
    total_errors = sum(len(s["errors"]) for s in all_stats)

    print(f"PDFs Processed: {len(all_stats)}")
    print(f"Total Series Extracted: {total_series}")
    print(f"Total Charts Found: {total_charts}")
    print(f"Total Forecast Tables: {total_tables}")
    if llm:
        print(f"LLM Enhanced Series: {total_llm}")

    if total_errors > 0:
        print(f"Errors: {total_errors}")
        for stats in all_stats:
            for error in stats["errors"]:
                print(f"  - {stats['pdf']}: {error}")

    print(f"\nOutput files saved to: {Path('output').absolute()}")

    # Cleanup
    if llm:
        llm.close()
    if not args.no_db:
        db.close()

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
