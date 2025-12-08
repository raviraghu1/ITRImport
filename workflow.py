#!/usr/bin/env python3
"""
ITR Import Workflow - Automated End-to-End PDF Processing

This workflow automatically processes uploaded PDF files through the complete
extraction, enhancement, storage, and consolidation pipeline.

Usage:
    # Process a single PDF through complete workflow
    python workflow.py --pdf "Files/report.pdf"

    # Process all PDFs in a directory
    python workflow.py --dir Files/

    # Watch directory for new PDFs (continuous monitoring)
    python workflow.py --watch Files/

    # Skip optional steps
    python workflow.py --pdf "report.pdf" --no-llm --no-consolidate

Pipeline Steps:
    1. PDF Extraction (PyMuPDF) - Extract text, charts, tables
    2. LLM Enhancement (Azure OpenAI) - Intelligent content extraction
    3. MongoDB Import - Store in sector collections
    4. Consolidation - Create single document per PDF
    5. Report Generation - JSON, CSV, TXT outputs
"""

import argparse
import json
import os
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.enhanced_parser import EnhancedITRParser
from src.enhanced_analyzer import EnhancedITRAnalyzer
from src.llm_extractor import LLMExtractor
from src.database import ITRDatabase
from src.models import Sector, EconomicSeries, ForecastRange

# MongoDB imports for consolidation
from pymongo import MongoClient, ASCENDING
from pymongo.database import Database


@dataclass
class WorkflowResult:
    """Result of processing a single PDF."""
    pdf_path: str
    pdf_filename: str
    report_id: str
    report_period: str
    success: bool

    # Extraction stats
    series_extracted: int = 0
    charts_found: int = 0
    forecast_tables: int = 0
    llm_enhanced: int = 0

    # Storage stats
    mongodb_documents: int = 0
    consolidated: bool = False

    # Output files
    output_files: list = None

    # Timing
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0

    # Errors
    errors: list = None

    def __post_init__(self):
        if self.output_files is None:
            self.output_files = []
        if self.errors is None:
            self.errors = []


class ITRWorkflow:
    """
    End-to-end workflow for processing ITR Economics PDF reports.

    Handles the complete pipeline from PDF upload to consolidated MongoDB documents.
    """

    def __init__(
        self,
        mongodb_uri: str = None,
        database_name: str = "ITRReports",
        output_dir: Path = None,
        use_llm: bool = True,
        verbose: bool = True
    ):
        self.mongodb_uri = mongodb_uri or os.getenv("ITR_MONGODB_URI", "mongodb://localhost:27017")
        self.database_name = database_name or os.getenv("ITR_DATABASE_NAME", "ITRReports")
        self.output_dir = output_dir or Path("output")
        self.use_llm = use_llm
        self.verbose = verbose

        # Initialize connections
        self.db: Optional[ITRDatabase] = None
        self.mongo_client: Optional[MongoClient] = None
        self.mongo_db: Optional[Database] = None
        self.llm: Optional[LLMExtractor] = None

        # Track processed files
        self.processed_files: set = set()

    def connect(self):
        """Initialize all connections."""
        # MongoDB via ITRDatabase for series storage
        self.db = ITRDatabase(self.mongodb_uri)
        try:
            self.db.connect()
            if self.verbose:
                print(f"Connected to MongoDB: {self.database_name}")
        except Exception as e:
            print(f"Warning: MongoDB connection failed: {e}")
            self.db = None

        # Direct MongoDB connection for consolidation
        try:
            self.mongo_client = MongoClient(self.mongodb_uri)
            self.mongo_db = self.mongo_client[self.database_name]
            # Test connection
            self.mongo_client.admin.command('ping')
            self._setup_collections()
        except Exception as e:
            print(f"Warning: Direct MongoDB connection failed: {e}")
            self.mongo_db = None

        # LLM Extractor
        if self.use_llm:
            try:
                self.llm = LLMExtractor()
                if self.verbose:
                    print("LLM Extractor initialized (Azure OpenAI GPT-4)")
            except Exception as e:
                print(f"Warning: LLM initialization failed: {e}")
                self.llm = None

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "consolidated").mkdir(exist_ok=True)

    def _setup_collections(self):
        """Ensure MongoDB collections and indexes exist."""
        if self.mongo_db is None:
            return

        # Consolidated collection
        coll = self.mongo_db["reports_consolidated"]
        coll.create_index([("report_id", ASCENDING)], unique=True, name="report_id_idx")
        coll.create_index([("report_period", ASCENDING)], name="period_idx")
        coll.create_index([("pdf_filename", ASCENDING)], name="filename_idx")

    def close(self):
        """Clean up connections."""
        if self.db:
            self.db.close()
        if self.llm:
            self.llm.close()
        if self.mongo_client:
            self.mongo_client.close()

    def process_pdf(self, pdf_path: Path, consolidate: bool = True) -> WorkflowResult:
        """
        Process a single PDF through the complete workflow.

        Args:
            pdf_path: Path to the PDF file
            consolidate: Whether to create consolidated document

        Returns:
            WorkflowResult with processing statistics
        """
        start_time = datetime.now()

        # Initialize result
        result = WorkflowResult(
            pdf_path=str(pdf_path),
            pdf_filename=pdf_path.name,
            report_id=pdf_path.stem.replace(" ", "_").lower(),
            report_period="Unknown",
            success=False,
            start_time=start_time.isoformat()
        )

        if self.verbose:
            print(f"\n{'='*70}")
            print(f"WORKFLOW: Processing {pdf_path.name}")
            print(f"{'='*70}")

        try:
            # === STEP 1: PDF Extraction ===
            if self.verbose:
                print("\n[1/5] Extracting PDF content...")

            series_list, report_metadata = self._extract_pdf(pdf_path, result)
            result.report_period = report_metadata.get("report_period", "Unknown")

            # === STEP 2: LLM Enhancement ===
            if self.llm and self.use_llm:
                if self.verbose:
                    print("\n[2/5] Enhancing with LLM...")
                self._enhance_with_llm(pdf_path, series_list, report_metadata, result)
            else:
                if self.verbose:
                    print("\n[2/5] Skipping LLM enhancement...")

            # === STEP 3: Generate Reports ===
            if self.verbose:
                print("\n[3/5] Generating reports...")
            self._generate_reports(series_list, report_metadata, pdf_path, result)

            # === STEP 4: Store in MongoDB ===
            if self.db and self.db.db is not None:
                if self.verbose:
                    print("\n[4/5] Storing in MongoDB...")
                self._store_in_mongodb(series_list, report_metadata, result)
            else:
                if self.verbose:
                    print("\n[4/5] Skipping MongoDB storage (not connected)...")

            # === STEP 5: Create Consolidated Document ===
            if consolidate and self.mongo_db is not None:
                if self.verbose:
                    print("\n[5/5] Creating consolidated document...")
                self._create_consolidated_document(series_list, report_metadata, result)
            else:
                if self.verbose:
                    print("\n[5/5] Skipping consolidation...")

            result.success = True

        except Exception as e:
            result.errors.append(str(e))
            if self.verbose:
                print(f"\nERROR: {e}")
                import traceback
                traceback.print_exc()

        # Calculate duration
        end_time = datetime.now()
        result.end_time = end_time.isoformat()
        result.duration_seconds = (end_time - start_time).total_seconds()

        # Mark as processed
        self.processed_files.add(str(pdf_path.absolute()))

        # Print summary
        if self.verbose:
            self._print_result_summary(result)

        return result

    def _extract_pdf(self, pdf_path: Path, result: WorkflowResult) -> tuple:
        """Extract content from PDF."""
        with EnhancedITRParser(pdf_path) as parser:
            if self.verbose:
                print(f"  Report Period: {parser.report_period}")
                print(f"  Total Pages: {parser.get_page_count()}")

            # Get metadata
            report_metadata = parser.get_report_metadata()

            # Extract series
            series_list = parser.extract_all_series()
            result.series_extracted = len(series_list)

            # Count charts and tables
            for series in series_list:
                result.charts_found += len(series.charts)
                if series.forecast_table:
                    result.forecast_tables += 1

            if self.verbose:
                print(f"  Series: {result.series_extracted}")
                print(f"  Charts: {result.charts_found}")
                print(f"  Forecast Tables: {result.forecast_tables}")

            return series_list, report_metadata

    def _enhance_with_llm(self, pdf_path: Path, series_list: list, report_metadata: dict, result: WorkflowResult):
        """Enhance extraction with LLM."""
        import fitz

        doc = fitz.open(pdf_path)

        for series in series_list:
            try:
                page_num = series.source.page_number - 1 if series.source else 0
                page_text = doc[page_num].get_text()

                llm_data = self.llm.extract_series_data(page_text, series.series_name)

                if llm_data:
                    # Merge LLM data
                    if not series.highlights and llm_data.get('highlights'):
                        series.highlights = llm_data['highlights']
                    if not series.management_objective and llm_data.get('management_objective'):
                        series.management_objective = llm_data['management_objective']
                    if not series.overview_text and llm_data.get('overview'):
                        series.overview_text = llm_data['overview']

                    # Enhanced forecasts
                    if llm_data.get('forecasts') and len(llm_data['forecasts']) > len(series.forecasts):
                        for f in llm_data['forecasts']:
                            if isinstance(f, dict) and f.get('year'):
                                series.forecasts.append(ForecastRange(
                                    year=f['year'],
                                    metric_type="12/12",
                                    value_point=f.get('rate_12_12')
                                ))

                    result.llm_enhanced += 1

            except Exception as e:
                if self.verbose:
                    print(f"  LLM error for {series.series_name}: {e}")

        # Executive summary
        try:
            for page_num in range(min(10, doc.page_count)):
                page_text = doc[page_num].get_text()
                if "Executive Summary" in page_text:
                    exec_summary = self.llm.extract_executive_summary(page_text)
                    if exec_summary:
                        report_metadata['executive_summary_enhanced'] = exec_summary
                    break
        except Exception as e:
            if self.verbose:
                print(f"  Executive summary error: {e}")

        doc.close()

        if self.verbose:
            print(f"  Enhanced: {result.llm_enhanced} series")

    def _generate_reports(self, series_list: list, report_metadata: dict, pdf_path: Path, result: WorkflowResult):
        """Generate output reports."""
        analyzer = EnhancedITRAnalyzer(series_list, report_metadata)
        report_name = pdf_path.stem.replace(" ", "_")

        # Text report
        report_path = self.output_dir / f"{report_name}_enhanced_report.txt"
        analyzer.generate_detailed_report(report_path)
        result.output_files.append(str(report_path))

        # JSON export
        json_path = self.output_dir / f"{report_name}_enhanced_data.json"
        analyzer.export_to_json(json_path)
        result.output_files.append(str(json_path))

        # CSV export
        csv_path = self.output_dir / f"{report_name}_enhanced_summary.csv"
        analyzer.export_to_csv(csv_path)
        result.output_files.append(str(csv_path))

        # Charts manifest
        charts_path = self.output_dir / f"{report_name}_charts_manifest.json"
        analyzer.export_charts_manifest(charts_path)
        result.output_files.append(str(charts_path))

        # Forecast tables
        tables_path = self.output_dir / f"{report_name}_forecast_tables.json"
        analyzer.export_forecast_tables(tables_path)
        result.output_files.append(str(tables_path))

        if self.verbose:
            print(f"  Generated {len(result.output_files)} output files")

    def _store_in_mongodb(self, series_list: list, report_metadata: dict, result: WorkflowResult):
        """Store extracted data in MongoDB."""
        count = 0

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
            self.db.upsert_series(basic_series)
            count += 1

        self.db.save_report_metadata(report_metadata)
        result.mongodb_documents = count + 1  # series + metadata

        if self.verbose:
            print(f"  Stored {count} series + metadata")

    def _create_consolidated_document(self, series_list: list, report_metadata: dict, result: WorkflowResult):
        """Create a single consolidated document for downstream use."""
        pdf_filename = report_metadata.get("pdf_filename", "")
        report_period = report_metadata.get("report_period", "Unknown")
        report_id = Path(pdf_filename).stem.replace(" ", "_").lower()

        # Organize series by sector
        sectors = {
            "core": [],
            "financial": [],
            "construction": [],
            "manufacturing": []
        }

        for series in series_list:
            sector = series.sector.value if hasattr(series.sector, 'value') else str(series.sector)
            if sector in sectors:
                # Convert to dict for storage
                series_dict = {
                    "series_id": series.series_id,
                    "series_name": series.series_name,
                    "sector": sector,
                    "unit": series.unit,
                    "current_value": series.current_value,
                    "current_period": series.current_period,
                    "rate_12_12": series.rate_12_12,
                    "current_phase": series.current_phase.value if hasattr(series.current_phase, 'value') and series.current_phase else None,
                    "forecasts": [
                        {
                            "year": f.year,
                            "metric_type": f.metric_type,
                            "value_point": f.value_point
                        } for f in series.forecasts
                    ],
                    "highlights": series.highlights,
                    "management_objective": series.management_objective,
                    "overview_text": getattr(series, 'overview_text', None),
                    "charts": [
                        {
                            "chart_type": c.chart_type,
                            "page_number": c.page_number,
                            "title": c.title,
                            "width": c.width,
                            "height": c.height
                        } for c in series.charts
                    ] if series.charts else []
                }
                sectors[sector].append(series_dict)

        # Get charts from analyzer export
        charts = []
        for series in series_list:
            for chart in series.charts:
                charts.append({
                    "series_id": series.series_id,
                    "series_name": series.series_name,
                    "chart_type": chart.chart_type,
                    "page_number": chart.page_number,
                    "title": chart.title,
                    "width": chart.width,
                    "height": chart.height
                })

        # Build consolidated document
        consolidated = {
            "report_id": report_id,
            "pdf_filename": pdf_filename,
            "report_period": report_period,

            "metadata": {
                "page_count": report_metadata.get("page_count"),
                "extraction_timestamp": report_metadata.get("extraction_timestamp"),
                "workflow_timestamp": datetime.now().isoformat(),
                "llm_enhanced": result.llm_enhanced > 0
            },

            "executive_summary": report_metadata.get("executive_summary") or report_metadata.get("executive_summary_enhanced"),

            "statistics": {
                "total_series": len(series_list),
                "series_by_sector": {k: len(v) for k, v in sectors.items()},
                "total_charts": result.charts_found,
                "total_forecast_tables": result.forecast_tables,
                "llm_enhanced_series": result.llm_enhanced
            },

            "sectors": {
                sector: {
                    "series_count": len(series_list_for_sector),
                    "series": series_list_for_sector
                }
                for sector, series_list_for_sector in sectors.items()
            },

            "charts": charts,

            "series_index": {
                "all_series_names": sorted(set(s.series_name for s in series_list)),
                "by_sector": {
                    sector: [s["series_name"] for s in series_list_for_sector]
                    for sector, series_list_for_sector in sectors.items()
                }
            }
        }

        # Store in MongoDB
        if self.mongo_db is not None:
            self.mongo_db["reports_consolidated"].update_one(
                {"report_id": report_id},
                {"$set": consolidated},
                upsert=True
            )
            result.consolidated = True

        # Also save to JSON file
        consolidated_path = self.output_dir / "consolidated" / f"{report_id}_consolidated.json"
        with open(consolidated_path, "w", encoding="utf-8") as f:
            json.dump(consolidated, f, indent=2, ensure_ascii=False, default=str)
        result.output_files.append(str(consolidated_path))

        if self.verbose:
            print(f"  Consolidated document created: {report_id}")

    def _print_result_summary(self, result: WorkflowResult):
        """Print processing result summary."""
        print(f"\n{'='*70}")
        print(f"WORKFLOW COMPLETE: {result.pdf_filename}")
        print(f"{'='*70}")
        print(f"  Report ID: {result.report_id}")
        print(f"  Report Period: {result.report_period}")
        print(f"  Status: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"  Duration: {result.duration_seconds:.1f} seconds")
        print(f"\n  Extraction:")
        print(f"    Series: {result.series_extracted}")
        print(f"    Charts: {result.charts_found}")
        print(f"    Forecast Tables: {result.forecast_tables}")
        print(f"    LLM Enhanced: {result.llm_enhanced}")
        print(f"\n  Storage:")
        print(f"    MongoDB Documents: {result.mongodb_documents}")
        print(f"    Consolidated: {'Yes' if result.consolidated else 'No'}")
        print(f"\n  Output Files: {len(result.output_files)}")
        for f in result.output_files:
            print(f"    - {Path(f).name}")
        if result.errors:
            print(f"\n  Errors: {len(result.errors)}")
            for e in result.errors:
                print(f"    - {e}")

    def process_directory(self, directory: Path, consolidate: bool = True) -> list[WorkflowResult]:
        """Process all PDFs in a directory."""
        results = []
        pdf_files = sorted(directory.glob("*.pdf"))

        if not pdf_files:
            print(f"No PDF files found in {directory}")
            return results

        print(f"\nFound {len(pdf_files)} PDF file(s) to process")

        for pdf_path in pdf_files:
            result = self.process_pdf(pdf_path, consolidate)
            results.append(result)

        # Print batch summary
        self._print_batch_summary(results)

        return results

    def _print_batch_summary(self, results: list[WorkflowResult]):
        """Print summary for batch processing."""
        print(f"\n{'='*70}")
        print("BATCH PROCESSING COMPLETE")
        print(f"{'='*70}")

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        total_series = sum(r.series_extracted for r in results)
        total_charts = sum(r.charts_found for r in results)
        total_tables = sum(r.forecast_tables for r in results)
        total_llm = sum(r.llm_enhanced for r in results)
        total_consolidated = sum(1 for r in results if r.consolidated)
        total_duration = sum(r.duration_seconds for r in results)

        print(f"\n  PDFs Processed: {len(results)} ({successful} successful, {failed} failed)")
        print(f"  Total Duration: {total_duration:.1f} seconds")
        print(f"\n  Totals:")
        print(f"    Series Extracted: {total_series}")
        print(f"    Charts Found: {total_charts}")
        print(f"    Forecast Tables: {total_tables}")
        print(f"    LLM Enhanced: {total_llm}")
        print(f"    Consolidated Documents: {total_consolidated}")

        if failed > 0:
            print(f"\n  Failed PDFs:")
            for r in results:
                if not r.success:
                    print(f"    - {r.pdf_filename}: {r.errors[0] if r.errors else 'Unknown error'}")

    def watch_directory(self, directory: Path, poll_interval: int = 10, consolidate: bool = True):
        """
        Watch a directory for new PDF files and process them automatically.

        Args:
            directory: Directory to watch
            poll_interval: Seconds between checks for new files
            consolidate: Whether to create consolidated documents
        """
        print(f"\n{'='*70}")
        print(f"WATCHING DIRECTORY: {directory}")
        print(f"Poll interval: {poll_interval} seconds")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*70}\n")

        # Initial scan
        existing_files = set(str(p.absolute()) for p in directory.glob("*.pdf"))
        self.processed_files.update(existing_files)
        print(f"Found {len(existing_files)} existing PDF file(s)")

        try:
            while True:
                # Check for new files
                current_files = set(str(p.absolute()) for p in directory.glob("*.pdf"))
                new_files = current_files - self.processed_files

                if new_files:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Found {len(new_files)} new file(s)")

                    for file_path in new_files:
                        pdf_path = Path(file_path)

                        # Wait a moment for file to be fully written
                        time.sleep(2)

                        result = self.process_pdf(pdf_path, consolidate)

                        if result.success:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Completed: {pdf_path.name}")
                        else:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed: {pdf_path.name}")

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            print("\n\nStopping file watcher...")

    def get_workflow_status(self) -> dict:
        """Get current workflow status."""
        status = {
            "mongodb_connected": self.db is not None and self.db.db is not None,
            "llm_available": self.llm is not None,
            "output_directory": str(self.output_dir),
            "processed_files": len(self.processed_files)
        }

        if self.mongo_db is not None:
            try:
                status["consolidated_documents"] = self.mongo_db["reports_consolidated"].count_documents({})
            except:
                status["consolidated_documents"] = 0

        return status


def main():
    """Main entry point for workflow."""
    parser = argparse.ArgumentParser(
        description="ITR Import Workflow - Automated End-to-End PDF Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python workflow.py --pdf "Files/report.pdf"    # Process single PDF
    python workflow.py --dir Files/                # Process all PDFs
    python workflow.py --watch Files/              # Watch for new PDFs
    python workflow.py --pdf "report.pdf" --no-llm # Skip LLM enhancement
        """
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("--pdf", type=Path, help="Process a single PDF file")
    input_group.add_argument("--dir", type=Path, help="Process all PDFs in directory")
    input_group.add_argument("--watch", type=Path, help="Watch directory for new PDFs")

    # Processing options
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM enhancement")
    parser.add_argument("--no-consolidate", action="store_true", help="Skip consolidation step")
    parser.add_argument("--no-db", action="store_true", help="Skip MongoDB storage")

    # Watch options
    parser.add_argument("--poll-interval", type=int, default=10,
                       help="Seconds between checks when watching (default: 10)")

    # Output options
    parser.add_argument("--output", type=Path, default=Path("output"),
                       help="Output directory (default: output/)")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")

    # Status
    parser.add_argument("--status", action="store_true", help="Show workflow status and exit")

    args = parser.parse_args()

    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║               ITR Import Workflow v2.1.0                        ║
    ║         Automated End-to-End PDF Processing                     ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    # Initialize workflow
    workflow = ITRWorkflow(
        output_dir=args.output,
        use_llm=not args.no_llm,
        verbose=not args.quiet
    )

    # Connect to services
    if not args.no_db:
        workflow.connect()
    else:
        # Still need LLM if requested
        if not args.no_llm:
            try:
                workflow.llm = LLMExtractor()
            except Exception as e:
                print(f"Warning: LLM initialization failed: {e}")

        workflow.output_dir.mkdir(parents=True, exist_ok=True)
        (workflow.output_dir / "consolidated").mkdir(exist_ok=True)

    # Show status and exit
    if args.status:
        status = workflow.get_workflow_status()
        print("\nWorkflow Status:")
        print(f"  MongoDB Connected: {status['mongodb_connected']}")
        print(f"  LLM Available: {status['llm_available']}")
        print(f"  Output Directory: {status['output_directory']}")
        print(f"  Consolidated Documents: {status.get('consolidated_documents', 'N/A')}")
        workflow.close()
        return 0

    try:
        # Require an input unless --status
        if not args.status and not args.pdf and not args.dir and not args.watch:
            parser.error("one of the arguments --pdf --dir --watch is required")

        # Process based on input type
        if args.pdf:
            if not args.pdf.exists():
                print(f"Error: PDF not found: {args.pdf}")
                return 1
            result = workflow.process_pdf(args.pdf, consolidate=not args.no_consolidate)
            return 0 if result.success else 1

        elif args.dir:
            if not args.dir.exists():
                print(f"Error: Directory not found: {args.dir}")
                return 1
            results = workflow.process_directory(args.dir, consolidate=not args.no_consolidate)
            return 0 if all(r.success for r in results) else 1

        elif args.watch:
            if not args.watch.exists():
                print(f"Error: Directory not found: {args.watch}")
                return 1
            workflow.watch_directory(
                args.watch,
                poll_interval=args.poll_interval,
                consolidate=not args.no_consolidate
            )
            return 0

    finally:
        workflow.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
