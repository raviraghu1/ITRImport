#!/usr/bin/env python3
"""
Create consolidated single documents per PDF file for downstream use.

This script creates a new 'reports_consolidated' collection where each document
represents a complete ITR Trends Report with all extracted data in one place.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.database import Database

load_dotenv()

MONGODB_URI = os.getenv("ITR_MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("ITR_DATABASE_NAME", "ITRReports")
CONSOLIDATED_COLLECTION = "reports_consolidated"


def connect_to_mongodb() -> tuple[MongoClient, Database]:
    """Connect to MongoDB."""
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    print(f"Connected to MongoDB: {DATABASE_NAME}")
    return client, db


def setup_consolidated_collection(db: Database):
    """Set up the consolidated reports collection."""
    coll = db[CONSOLIDATED_COLLECTION]

    # Create indexes
    coll.create_index([("report_id", ASCENDING)], unique=True, name="report_id_idx")
    coll.create_index([("report_period", ASCENDING)], name="period_idx")
    coll.create_index([("pdf_filename", ASCENDING)], name="filename_idx")

    print(f"Collection '{CONSOLIDATED_COLLECTION}' ready with indexes")
    return coll


def get_report_metadata(db: Database, pdf_filename: str) -> dict:
    """Get report metadata."""
    return db["reports"].find_one({"pdf_filename": pdf_filename}) or {}


def get_series_for_report(db: Database, report_period: str, pdf_filename: str) -> dict:
    """Get all series for a report, organized by sector."""
    sectors = {
        "core": [],
        "financial": [],
        "construction": [],
        "manufacturing": []
    }

    for sector in sectors.keys():
        coll = db[f"{sector}_series"]
        # Match by report period or pdf filename in source
        cursor = coll.find({
            "$or": [
                {"source.report_period": report_period},
                {"source.pdf_filename": pdf_filename}
            ]
        })

        for doc in cursor:
            # Remove MongoDB _id for cleaner document
            doc.pop("_id", None)
            sectors[sector].append(doc)

    return sectors


def get_charts_for_report(db: Database, report_period: str, pdf_filename: str) -> list:
    """Get all charts for a report."""
    charts = []
    cursor = db["charts"].find({
        "$or": [
            {"report_period": report_period},
            {"pdf_filename": pdf_filename}
        ]
    })

    for doc in cursor:
        doc.pop("_id", None)
        charts.append(doc)

    return charts


def get_forecast_tables_for_report(db: Database, source_report: str) -> list:
    """Get forecast tables for a report."""
    tables = []
    cursor = db["forecast_tables"].find({"source_report": source_report})

    for doc in cursor:
        doc.pop("_id", None)
        tables.append(doc)

    return tables


def create_consolidated_document(db: Database, report_meta: dict) -> dict:
    """Create a single consolidated document for a report."""

    pdf_filename = report_meta.get("pdf_filename", "")
    report_period = report_meta.get("report_period", "Unknown")

    # Create report ID from filename
    report_id = Path(pdf_filename).stem.replace(" ", "_").lower()

    # Get source report name for forecast tables lookup
    source_report = Path(pdf_filename).stem.replace(" ", "_")

    # Get all series by sector
    series_by_sector = get_series_for_report(db, report_period, pdf_filename)

    # Get all charts
    charts = get_charts_for_report(db, report_period, pdf_filename)

    # Get forecast tables
    forecast_tables = get_forecast_tables_for_report(db, source_report)

    # Calculate statistics
    total_series = sum(len(s) for s in series_by_sector.values())

    # Build consolidated document
    consolidated = {
        # Identification
        "report_id": report_id,
        "pdf_filename": pdf_filename,
        "report_period": report_period,

        # Metadata
        "metadata": {
            "page_count": report_meta.get("page_count"),
            "extraction_timestamp": report_meta.get("extraction_timestamp"),
            "import_timestamp": report_meta.get("import_timestamp"),
            "consolidated_timestamp": datetime.now().isoformat()
        },

        # Executive Summary
        "executive_summary": report_meta.get("executive_summary") or report_meta.get("executive_summary_enhanced"),

        # Statistics
        "statistics": {
            "total_series": total_series,
            "series_by_sector": {k: len(v) for k, v in series_by_sector.items()},
            "total_charts": len(charts),
            "total_forecast_tables": len(forecast_tables)
        },

        # Series Data by Sector
        "sectors": {
            "core": {
                "series_count": len(series_by_sector["core"]),
                "series": series_by_sector["core"]
            },
            "financial": {
                "series_count": len(series_by_sector["financial"]),
                "series": series_by_sector["financial"]
            },
            "construction": {
                "series_count": len(series_by_sector["construction"]),
                "series": series_by_sector["construction"]
            },
            "manufacturing": {
                "series_count": len(series_by_sector["manufacturing"]),
                "series": series_by_sector["manufacturing"]
            }
        },

        # All Charts
        "charts": charts,

        # Forecast Tables
        "forecast_tables": forecast_tables,

        # Quick Reference Lists
        "series_index": {
            "all_series_names": [],
            "by_sector": {}
        }
    }

    # Build series index for quick lookup
    all_names = []
    by_sector = {}
    for sector, series_list in series_by_sector.items():
        sector_names = [s.get("series_name") for s in series_list if s.get("series_name")]
        all_names.extend(sector_names)
        by_sector[sector] = sector_names

    consolidated["series_index"]["all_series_names"] = sorted(set(all_names))
    consolidated["series_index"]["by_sector"] = by_sector

    return consolidated


def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║         Create Consolidated Report Documents                ║
    ║           One Document Per PDF for Downstream Use           ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    # Connect to MongoDB
    client, db = connect_to_mongodb()

    # Setup collection
    coll = setup_consolidated_collection(db)

    # Get all reports
    reports = list(db["reports"].find())
    print(f"\nFound {len(reports)} reports to consolidate")

    # Process each report
    for report_meta in reports:
        pdf_filename = report_meta.get("pdf_filename", "Unknown")
        print(f"\nProcessing: {pdf_filename}")

        # Create consolidated document
        consolidated = create_consolidated_document(db, report_meta)

        # Upsert to collection
        result = coll.update_one(
            {"report_id": consolidated["report_id"]},
            {"$set": consolidated},
            upsert=True
        )

        stats = consolidated["statistics"]
        print(f"  Report ID: {consolidated['report_id']}")
        print(f"  Period: {consolidated['report_period']}")
        print(f"  Series: {stats['total_series']} ({stats['series_by_sector']})")
        print(f"  Charts: {stats['total_charts']}")
        print(f"  Forecast Tables: {stats['total_forecast_tables']}")

        if result.upserted_id:
            print(f"  Status: CREATED")
        else:
            print(f"  Status: UPDATED")

    # Show final statistics
    print("\n" + "=" * 60)
    print("CONSOLIDATION COMPLETE")
    print("=" * 60)

    total_docs = coll.count_documents({})
    print(f"\nCollection: {CONSOLIDATED_COLLECTION}")
    print(f"Total Documents: {total_docs}")

    print("\nConsolidated Reports:")
    for doc in coll.find({}, {"report_id": 1, "report_period": 1, "statistics": 1, "_id": 0}):
        print(f"  • {doc['report_id']}")
        print(f"    Period: {doc['report_period']}")
        print(f"    Series: {doc['statistics']['total_series']}, Charts: {doc['statistics']['total_charts']}")

    # Also export to JSON files for reference
    output_dir = Path("output/consolidated")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nExporting to JSON files in {output_dir}/")
    for doc in coll.find():
        doc.pop("_id", None)
        output_file = output_dir / f"{doc['report_id']}_consolidated.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False, default=str)
        print(f"  Exported: {output_file.name}")

    client.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
