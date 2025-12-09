"""
ITR Economics PDF Parser.

Per Constitution Principle I (Data Fidelity):
Extract data preserving original values, units, and precision.

Per Constitution Principle II (Source Traceability):
Track source PDF, page number, and extraction timestamp.
"""

import re
import fitz  # PyMuPDF
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import (
    EconomicSeries, Sector, BusinessPhase, SourceMetadata,
    ForecastRange, AtAGlanceSummary
)


class ITRParser:
    """Parser for ITR Economics Trends Report PDFs."""

    # Series name patterns and their sectors
    SERIES_PATTERNS = {
        # Core
        r"US Industrial Production": Sector.CORE,
        r"US Nondefense Capital Goods New Orders": Sector.CORE,
        r"US Private Sector Employment": Sector.CORE,
        r"US Total Retail Sales": Sector.CORE,
        r"US Wholesale Trade of Durable Goods": Sector.CORE,
        r"US Wholesale Trade of Nondurable Goods": Sector.CORE,
        r"ITR Leading Indicator": Sector.CORE,
        r"US Total Industry Capacity Utilization Rate": Sector.CORE,
        r"US OECD Leading Indicator": Sector.CORE,
        r"US ISM PMI": Sector.CORE,

        # Financial
        r"US Stock Prices|S&P 500": Sector.FINANCIAL,
        r"US Government Long-Term Bond Yields": Sector.FINANCIAL,
        r"US Natural Gas Spot Prices": Sector.FINANCIAL,
        r"US Crude Oil Spot Prices": Sector.FINANCIAL,
        r"US Steel Scrap Producer Price": Sector.FINANCIAL,
        r"US Consumer Price Index": Sector.FINANCIAL,
        r"US Producer Price Index": Sector.FINANCIAL,

        # Construction
        r"US Single-Unit Housing Starts": Sector.CONSTRUCTION,
        r"US Multi-Unit Housing Starts": Sector.CONSTRUCTION,
        r"US Private Office Construction": Sector.CONSTRUCTION,
        r"US Total Education Construction": Sector.CONSTRUCTION,
        r"US Total Hospital Construction": Sector.CONSTRUCTION,
        r"US Private Manufacturing Construction": Sector.CONSTRUCTION,
        r"US Private Multi-Tenant Retail Construction": Sector.CONSTRUCTION,
        r"US Private Warehouse Construction": Sector.CONSTRUCTION,
        r"US Public Water.*Sewer.*Construction": Sector.CONSTRUCTION,

        # Manufacturing
        r"US Metalworking Machinery New Orders": Sector.MANUFACTURING,
        r"US Machinery New Orders": Sector.MANUFACTURING,
        r"US Construction Machinery New Orders": Sector.MANUFACTURING,
        r"US Electrical Equipment New Orders": Sector.MANUFACTURING,
        r"US Computers.*Electronics New Orders": Sector.MANUFACTURING,
        r"US Defense Capital Goods New Orders": Sector.MANUFACTURING,
        r"North America Light Vehicle Production": Sector.MANUFACTURING,
        r"US Oil.*Gas Extraction Production": Sector.MANUFACTURING,
        r"US Mining Production": Sector.MANUFACTURING,
        r"US Chemicals.*Chemical Products Production": Sector.MANUFACTURING,
        r"US Civilian Aircraft.*Production": Sector.MANUFACTURING,
        r"US Medical Equipment.*Supplies Production": Sector.MANUFACTURING,
        r"US Heavy-Duty Truck Production": Sector.MANUFACTURING,
        r"US Food Production": Sector.MANUFACTURING,
    }

    # Patterns for extracting data
    FORECAST_PATTERN = re.compile(
        r"(\d{4}):\s*\n?\s*12/12\s*\n?\s*12MM[AT]\s*\n?\s*"
        r"(-?\d+\.?\d*)%?\s*\n?\s*\$?([\d,\.]+)"
    )

    RATE_OF_CHANGE_PATTERN = re.compile(
        r"(\d+)/12.*?(-?\d+\.?\d*)%"
    )

    PHASE_PATTERN = re.compile(
        r"Phase\s+([ABCD])"
    )

    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path)
        self.doc = None
        self.report_period = None
        self.extraction_timestamp = datetime.now()

    def open(self):
        """Open the PDF document."""
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        self.doc = fitz.open(self.pdf_path)
        self._detect_report_period()

    def close(self):
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
            self.doc = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _detect_report_period(self):
        """Detect the report period from the first few pages."""
        if not self.doc:
            return

        for page_num in range(min(3, len(self.doc))):
            text = self.doc[page_num].get_text()
            # Look for patterns like "March 2024"
            match = re.search(
                r"(January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+(\d{4})",
                text
            )
            if match:
                self.report_period = f"{match.group(1)} {match.group(2)}"
                break

    def _create_source_metadata(self, page_number: int) -> SourceMetadata:
        """Create source metadata for traceability."""
        return SourceMetadata(
            pdf_filename=self.pdf_path.name,
            page_number=page_number,
            extraction_timestamp=self.extraction_timestamp,
            report_period=self.report_period or "Unknown"
        )

    def _detect_sector(self, text: str) -> Optional[Sector]:
        """Detect which sector a page belongs to."""
        text_lower = text.lower()
        if "core" in text_lower and "/    march" in text_lower:
            return Sector.CORE
        elif "financial" in text_lower and "/    march" in text_lower:
            return Sector.FINANCIAL
        elif "construction" in text_lower and "/    march" in text_lower:
            return Sector.CONSTRUCTION
        elif "manufacturing" in text_lower and "/    march" in text_lower:
            return Sector.MANUFACTURING
        return None

    def _extract_series_name(self, text: str) -> Optional[tuple[str, Sector]]:
        """Extract the series name and sector from page text."""
        for pattern, sector in self.SERIES_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0), sector
        return None

    def _extract_unit(self, text: str) -> str:
        """Extract the unit of measurement."""
        patterns = [
            r"Index,\s*\d{4}\s*=\s*\d+",
            r"Billions of Dollars",
            r"Millions of (?:Units|Employees)",
            r"Thousands of Units",
            r"Trillions of Dollars",
            r"Percent",
            r"Dollars per (?:Barrel|MMBtu)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return "Unknown"

    def _extract_forecasts(self, text: str) -> list[ForecastRange]:
        """Extract forecast data from page text."""
        forecasts = []

        # Pattern for year forecasts with 12/12 and 12MMA/12MMT
        forecast_blocks = re.findall(
            r"(\d{4}):\s*\n?\s*12/12\s*\n?\s*12MM[AT]\s*\n?\s*"
            r"(-?\d+\.?\d*)%?\s*\n?\s*\$?([\d,\.]+)",
            text, re.DOTALL
        )

        for year, rate, value in forecast_blocks:
            try:
                forecasts.append(ForecastRange(
                    year=int(year),
                    metric_type="12/12",
                    value_point=float(rate.replace(",", ""))
                ))
                forecasts.append(ForecastRange(
                    year=int(year),
                    metric_type="12MMA",
                    value_point=float(value.replace(",", "").replace("$", ""))
                ))
            except ValueError:
                continue

        return forecasts

    def _extract_highlights(self, text: str) -> list[str]:
        """Extract bullet point highlights."""
        highlights = []
        # Look for bullet points (• character or similar)
        bullets = re.findall(r"[•\-]\s*(.+?)(?=\n[•\-]|\nAsk an Analyst|$)", text, re.DOTALL)
        for bullet in bullets[:5]:  # Limit to first 5
            cleaned = bullet.strip().replace("\n", " ")
            if len(cleaned) > 20:  # Skip very short fragments
                highlights.append(cleaned)
        return highlights

    def _extract_management_objective(self, text: str) -> Optional[str]:
        """Extract the ITR Management Objective."""
        match = re.search(
            r"ITR MANAGEMENT OBJECTIVE\s*\n?\s*(.+?)(?=\n[•\-]|FORECAST|$)",
            text, re.DOTALL | re.IGNORECASE
        )
        if match:
            return match.group(1).strip().replace("\n", " ")
        return None

    def extract_series_from_page(self, page_num: int) -> Optional[EconomicSeries]:
        """Extract economic series data from a single page."""
        if not self.doc or page_num >= len(self.doc):
            return None

        page = self.doc[page_num]
        text = page.get_text()

        # Try to identify the series
        series_info = self._extract_series_name(text)
        if not series_info:
            return None

        series_name, sector = series_info

        # Create series ID from name
        series_id = re.sub(r"[^a-zA-Z0-9]", "_", series_name).lower()

        series = EconomicSeries(
            series_id=series_id,
            series_name=series_name,
            sector=sector,
            unit=self._extract_unit(text),
            source=self._create_source_metadata(page_num + 1)  # 1-indexed
        )

        # Extract forecasts
        series.forecasts = self._extract_forecasts(text)

        # Extract highlights
        series.highlights = self._extract_highlights(text)

        # Extract management objective
        series.management_objective = self._extract_management_objective(text)

        return series

    def extract_all_series(self) -> list[EconomicSeries]:
        """Extract all economic series from the PDF."""
        if not self.doc:
            raise RuntimeError("PDF not opened. Call open() first.")

        series_list = []
        seen_series = set()

        for page_num in range(len(self.doc)):
            series = self.extract_series_from_page(page_num)
            if series and series.series_id not in seen_series:
                series_list.append(series)
                seen_series.add(series.series_id)

        return series_list

    def extract_executive_summary(self) -> Optional[str]:
        """Extract the executive summary text."""
        if not self.doc:
            return None

        for page_num in range(min(10, len(self.doc))):
            text = self.doc[page_num].get_text()
            if "Executive Summary" in text:
                # Extract text after "Executive Summary" header
                match = re.search(
                    r"Executive Summary\s*\n?\s*BY:.*?\n(.+?)(?=\n\n\n|$)",
                    text, re.DOTALL
                )
                if match:
                    return match.group(1).strip()
        return None

    def get_page_count(self) -> int:
        """Get the total number of pages."""
        return len(self.doc) if self.doc else 0

    def get_report_metadata(self) -> dict:
        """Get report-level metadata."""
        return {
            "pdf_filename": self.pdf_path.name,
            "report_period": self.report_period,
            "page_count": self.get_page_count(),
            "extraction_timestamp": self.extraction_timestamp.isoformat()
        }
