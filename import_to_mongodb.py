#!/usr/bin/env python3
"""
Import all extracted ITR data into MongoDB ITRReports database.

This script imports:
- All enhanced JSON data files from output/
- Charts manifests
- Forecast tables
- Report metadata
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient, ASCENDING
from pymongo.database import Database


# MongoDB connection - load from environment
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file if present

MONGODB_URI = os.getenv("ITR_MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("ITR_DATABASE_NAME", "ITRReports")


def connect_to_mongodb() -> tuple[MongoClient, Database]:
    """Connect to MongoDB and return client and database."""
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    print(f"Connected to MongoDB: {DATABASE_NAME}")
    return client, db


def setup_collections(db: Database):
    """Create collections with indexes."""

    # Economic Series by Sector
    collections = [
        "core_series",
        "financial_series",
        "construction_series",
        "manufacturing_series"
    ]

    for coll_name in collections:
        coll = db[coll_name]
        # Create indexes
        coll.create_index(
            [("series_id", ASCENDING), ("source.report_period", ASCENDING)],
            unique=True,
            name="series_period_idx"
        )
        coll.create_index([("series_name", ASCENDING)], name="name_idx")
        coll.create_index([("source.report_period", ASCENDING)], name="period_idx")
        print(f"  Created collection: {coll_name}")

    # Reports collection
    db["reports"].create_index(
        [("pdf_filename", ASCENDING), ("report_period", ASCENDING)],
        unique=True,
        name="report_idx"
    )
    print(f"  Created collection: reports")

    # Charts collection
    db["charts"].create_index(
        [("series_id", ASCENDING), ("page", ASCENDING), ("chart_type", ASCENDING)],
        name="chart_idx"
    )
    print(f"  Created collection: charts")

    # Forecast tables collection
    db["forecast_tables"].create_index(
        [("series_id", ASCENDING), ("source_report", ASCENDING)],
        name="forecast_idx"
    )
    print(f"  Created collection: forecast_tables")

    # Raw pages collection (for full context)
    db["pages"].create_index(
        [("pdf_filename", ASCENDING), ("page_number", ASCENDING)],
        unique=True,
        name="page_idx"
    )
    print(f"  Created collection: pages")


def get_sector_collection(db: Database, sector: str) -> str:
    """Get collection name for a sector."""
    sector_map = {
        "core": "core_series",
        "financial": "financial_series",
        "construction": "construction_series",
        "manufacturing": "manufacturing_series"
    }
    return sector_map.get(sector.lower(), "core_series")


def import_enhanced_data(db: Database, json_path: Path) -> dict:
    """Import enhanced data JSON file."""
    stats = {"series": 0, "charts": 0, "updated": 0}

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Import report metadata
    if data.get("report_metadata"):
        metadata = data["report_metadata"].copy()
        metadata["import_timestamp"] = datetime.now().isoformat()
        metadata["source_file"] = json_path.name

        db["reports"].update_one(
            {
                "pdf_filename": metadata.get("pdf_filename"),
                "report_period": metadata.get("report_period")
            },
            {"$set": metadata},
            upsert=True
        )

    # Import each series
    for series in data.get("series", []):
        sector = series.get("sector", "core")
        coll_name = get_sector_collection(db, sector)
        coll = db[coll_name]

        # Add import metadata
        series["import_timestamp"] = datetime.now().isoformat()
        series["source_file"] = json_path.name

        # Upsert the series
        result = coll.update_one(
            {
                "series_id": series.get("series_id"),
                "source.report_period": series.get("source", {}).get("report_period")
            },
            {"$set": series},
            upsert=True
        )

        if result.upserted_id:
            stats["series"] += 1
        else:
            stats["updated"] += 1

        # Import charts separately for easier querying
        for chart in series.get("charts", []):
            chart_doc = chart.copy()
            chart_doc["series_id"] = series.get("series_id")
            chart_doc["series_name"] = series.get("series_name")
            chart_doc["sector"] = sector
            chart_doc["report_period"] = series.get("source", {}).get("report_period")
            chart_doc["pdf_filename"] = series.get("source", {}).get("pdf_filename")

            db["charts"].update_one(
                {
                    "series_id": chart_doc["series_id"],
                    "page": chart_doc.get("page_number"),
                    "chart_type": chart_doc.get("chart_type"),
                    "report_period": chart_doc["report_period"]
                },
                {"$set": chart_doc},
                upsert=True
            )
            stats["charts"] += 1

    return stats


def import_charts_manifest(db: Database, manifest_path: Path) -> int:
    """Import charts manifest file."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract report info from filename
    report_name = manifest_path.stem.replace("_charts_manifest", "")

    count = 0
    for chart in data.get("charts", []):
        chart["source_manifest"] = manifest_path.name
        chart["report_name"] = report_name

        db["charts"].update_one(
            {
                "series_id": chart.get("series_id"),
                "page": chart.get("page"),
                "chart_type": chart.get("chart_type")
            },
            {"$set": chart},
            upsert=True
        )
        count += 1

    return count


def import_forecast_tables(db: Database, tables_path: Path) -> int:
    """Import forecast tables file."""
    with open(tables_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    report_name = tables_path.stem.replace("_forecast_tables", "")

    count = 0
    for table in data.get("tables", []):
        table["source_report"] = report_name
        table["import_timestamp"] = datetime.now().isoformat()

        db["forecast_tables"].update_one(
            {
                "series_id": table.get("series_id"),
                "source_report": report_name
            },
            {"$set": table},
            upsert=True
        )
        count += 1

    return count


def show_stats(db: Database):
    """Display database statistics."""
    print("\n" + "=" * 60)
    print("DATABASE STATISTICS: ITRReports")
    print("=" * 60)

    collections = [
        "reports",
        "core_series",
        "financial_series",
        "construction_series",
        "manufacturing_series",
        "charts",
        "forecast_tables"
    ]

    total = 0
    for coll_name in collections:
        count = db[coll_name].count_documents({})
        total += count
        print(f"  {coll_name:<25} {count:>6} documents")

    print("-" * 60)
    print(f"  {'TOTAL':<25} {total:>6} documents")

    # Show reports breakdown
    print("\n" + "-" * 40)
    print("REPORTS:")
    print("-" * 40)
    for report in db["reports"].find({}, {"pdf_filename": 1, "report_period": 1, "_id": 0}):
        print(f"  • {report.get('pdf_filename', 'Unknown')} ({report.get('report_period', 'N/A')})")

    # Show series by sector
    print("\n" + "-" * 40)
    print("SERIES BY SECTOR:")
    print("-" * 40)
    for sector in ["core", "financial", "construction", "manufacturing"]:
        coll = db[f"{sector}_series"]
        series_names = coll.distinct("series_name")
        print(f"\n  {sector.upper()} ({len(series_names)} unique series):")
        for name in sorted(series_names)[:10]:
            print(f"    - {name}")
        if len(series_names) > 10:
            print(f"    ... and {len(series_names) - 10} more")


def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║           ITRImport - MongoDB Import Utility                ║
    ║              Importing to ITRReports Database               ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    # Connect to MongoDB
    client, db = connect_to_mongodb()

    # Setup collections
    print("\nSetting up collections...")
    setup_collections(db)

    # Find all output files
    output_dir = Path("output")
    if not output_dir.exists():
        print("Error: output/ directory not found")
        return 1

    # Import enhanced data files
    print("\nImporting enhanced data files...")
    enhanced_files = list(output_dir.glob("*_enhanced_data.json"))

    total_stats = {"series": 0, "charts": 0, "updated": 0}

    for json_path in enhanced_files:
        print(f"\n  Processing: {json_path.name}")
        stats = import_enhanced_data(db, json_path)
        print(f"    Series: {stats['series']} new, {stats['updated']} updated")
        print(f"    Charts: {stats['charts']}")

        total_stats["series"] += stats["series"]
        total_stats["charts"] += stats["charts"]
        total_stats["updated"] += stats["updated"]

    # Import charts manifests
    print("\nImporting charts manifests...")
    manifest_files = list(output_dir.glob("*_charts_manifest.json"))

    for manifest_path in manifest_files:
        count = import_charts_manifest(db, manifest_path)
        print(f"  {manifest_path.name}: {count} charts")

    # Import forecast tables
    print("\nImporting forecast tables...")
    tables_files = list(output_dir.glob("*_forecast_tables.json"))

    for tables_path in tables_files:
        count = import_forecast_tables(db, tables_path)
        print(f"  {tables_path.name}: {count} tables")

    # Show final statistics
    show_stats(db)

    # Summary
    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"  New series imported: {total_stats['series']}")
    print(f"  Series updated: {total_stats['updated']}")
    print(f"  Charts imported: {total_stats['charts']}")
    print(f"  Files processed: {len(enhanced_files)}")

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
