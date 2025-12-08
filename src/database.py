"""
MongoDB database operations for ITR Economics data.

Per Constitution Principle III (Structured Data Model):
- MongoDB collections organized by data category
- Schema validation to prevent malformed data

Per Constitution Principle IV (Idempotent Processing):
- Upsert operations using composite keys
"""

import os
from datetime import datetime
from typing import Optional
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database

from .models import EconomicSeries, AtAGlanceSummary, Sector


class ITRDatabase:
    """MongoDB database handler for ITR Economics data."""

    DEFAULT_DB_NAME = "itr_economics"

    # Collection names by sector
    COLLECTIONS = {
        Sector.CORE: "core_series",
        Sector.FINANCIAL: "financial_series",
        Sector.CONSTRUCTION: "construction_series",
        Sector.MANUFACTURING: "manufacturing_series",
    }

    def __init__(self, connection_string: Optional[str] = None, db_name: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            connection_string: MongoDB connection string. Falls back to
                              ITR_MONGODB_URI environment variable.
            db_name: Database name. Defaults to 'itr_economics'.
        """
        self.connection_string = connection_string or os.getenv(
            "ITR_MONGODB_URI",
            "mongodb://localhost:27017"
        )
        self.db_name = db_name or self.DEFAULT_DB_NAME
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None

    def connect(self):
        """Establish database connection."""
        self.client = MongoClient(self.connection_string)
        self.db = self.client[self.db_name]
        self._ensure_indexes()
        print(f"Connected to MongoDB: {self.db_name}")

    def close(self):
        """Close database connection."""
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _ensure_indexes(self):
        """Create indexes for efficient querying."""
        if self.db is None:
            return

        for collection_name in self.COLLECTIONS.values():
            collection = self.db[collection_name]
            # Composite index for idempotent upserts
            collection.create_index(
                [("series_id", ASCENDING), ("source.report_period", ASCENDING)],
                unique=True,
                name="series_period_idx"
            )
            # Index for time-based queries
            collection.create_index(
                [("source.report_period", ASCENDING)],
                name="period_idx"
            )

        # Metadata collection
        self.db["report_metadata"].create_index(
            [("pdf_filename", ASCENDING), ("report_period", ASCENDING)],
            unique=True,
            name="report_idx"
        )

    def _get_collection(self, sector: Sector) -> Collection:
        """Get the collection for a given sector."""
        if self.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db[self.COLLECTIONS[sector]]

    def upsert_series(self, series: EconomicSeries) -> str:
        """
        Insert or update an economic series.

        Per Constitution Principle IV: Idempotent operation using
        composite key (series_id + report_period).

        Returns:
            The MongoDB document ID.
        """
        collection = self._get_collection(series.sector)
        doc = series.to_dict()

        # Use series_id + report_period as composite key
        filter_key = {
            "series_id": series.series_id,
            "source.report_period": series.source.report_period if series.source else None
        }

        result = collection.update_one(
            filter_key,
            {"$set": doc},
            upsert=True
        )

        return str(result.upserted_id or "updated")

    def upsert_many_series(self, series_list: list[EconomicSeries]) -> dict:
        """
        Insert or update multiple series.

        Returns:
            Summary of operations: {inserted: N, updated: N}
        """
        inserted = 0
        updated = 0

        for series in series_list:
            result = self.upsert_series(series)
            if result == "updated":
                updated += 1
            else:
                inserted += 1

        return {"inserted": inserted, "updated": updated}

    def save_report_metadata(self, metadata: dict):
        """Save report-level metadata."""
        if self.db is None:
            raise RuntimeError("Database not connected.")

        self.db["report_metadata"].update_one(
            {
                "pdf_filename": metadata["pdf_filename"],
                "report_period": metadata["report_period"]
            },
            {"$set": metadata},
            upsert=True
        )

    def get_series_by_id(self, series_id: str, sector: Sector) -> Optional[dict]:
        """Retrieve a series by its ID."""
        collection = self._get_collection(sector)
        return collection.find_one({"series_id": series_id})

    def get_series_by_period(self, report_period: str, sector: Optional[Sector] = None) -> list[dict]:
        """Get all series for a given report period."""
        results = []

        collections = [self.COLLECTIONS[sector]] if sector else self.COLLECTIONS.values()

        for collection_name in collections:
            cursor = self.db[collection_name].find(
                {"source.report_period": report_period}
            )
            results.extend(list(cursor))

        return results

    def get_all_series(self, sector: Optional[Sector] = None) -> list[dict]:
        """Get all series, optionally filtered by sector."""
        results = []

        if sector:
            collection = self._get_collection(sector)
            results = list(collection.find())
        else:
            for collection_name in self.COLLECTIONS.values():
                cursor = self.db[collection_name].find()
                results.extend(list(cursor))

        return results

    def get_series_history(self, series_id: str, sector: Sector) -> list[dict]:
        """Get all historical data for a series across report periods."""
        collection = self._get_collection(sector)
        cursor = collection.find({"series_id": series_id}).sort(
            "source.report_period", ASCENDING
        )
        return list(cursor)

    def get_stats(self) -> dict:
        """Get database statistics."""
        if self.db is None:
            return {}

        stats = {
            "database": self.db_name,
            "collections": {}
        }

        for sector, collection_name in self.COLLECTIONS.items():
            collection = self.db[collection_name]
            stats["collections"][collection_name] = {
                "count": collection.count_documents({}),
                "sector": sector.value
            }

        stats["collections"]["report_metadata"] = {
            "count": self.db["report_metadata"].count_documents({})
        }

        return stats
