"""
Enhanced ITR Economics PDF Parser with Chart and Table Context.

Per Constitution Principle I (Data Fidelity):
Extract data preserving original values, units, and precision.

Per Constitution Principle II (Source Traceability):
Track source PDF, page number, and extraction timestamp.

Per Constitution Principle V (Visualization Integrity):
Capture chart context and metadata for accurate reproduction.
"""

import re
import fitz  # PyMuPDF
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from .models import (
    EconomicSeries, Sector, BusinessPhase, SourceMetadata,
    ForecastRange, AtAGlanceSummary
)


@dataclass
class ChartMetadata:
    """Metadata about a chart/graph in the PDF."""
    chart_type: str  # "rate_of_change", "data_trend", "overview"
    title: str
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    image_xref: Optional[int] = None
    width: int = 0
    height: int = 0
    page_number: int = 0
    position: tuple = (0, 0, 0, 0)  # bbox

    def to_dict(self) -> dict:
        return {
            "chart_type": self.chart_type,
            "title": self.title,
            "x_axis_label": self.x_axis_label,
            "y_axis_label": self.y_axis_label,
            "image_xref": self.image_xref,
            "dimensions": {"width": self.width, "height": self.height},
            "page_number": self.page_number,
            "position": self.position
        }


@dataclass
class TableData:
    """Extracted table data with context."""
    table_type: str  # "forecast", "at_a_glance", "phase_summary"
    title: str
    headers: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    context: str = ""  # Surrounding text for context
    page_number: int = 0

    def to_dict(self) -> dict:
        return {
            "table_type": self.table_type,
            "title": self.title,
            "headers": self.headers,
            "rows": self.rows,
            "context": self.context,
            "page_number": self.page_number
        }


@dataclass
class EnhancedEconomicSeries:
    """Extended economic series with chart and table context."""
    series_id: str
    series_name: str
    sector: Sector
    unit: str

    # Current data
    current_value: Optional[float] = None
    current_period: Optional[str] = None

    # Rate of change metrics
    rate_12_12: Optional[float] = None
    rate_3_12: Optional[float] = None
    rate_1_12: Optional[float] = None

    # Business cycle phase
    current_phase: Optional[BusinessPhase] = None
    forecast_phases: dict = field(default_factory=dict)  # year -> phase

    # Forecasts with full context
    forecasts: list[ForecastRange] = field(default_factory=list)
    forecast_table: Optional[TableData] = None

    # Charts metadata
    charts: list[ChartMetadata] = field(default_factory=list)

    # Content sections
    overview_text: str = ""
    highlights: list[str] = field(default_factory=list)
    management_objective: str = ""
    data_trend_description: str = ""

    # At-a-Glance context
    at_a_glance_row: Optional[dict] = None

    # Source tracking
    source: Optional[SourceMetadata] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB storage."""
        return {
            "series_id": self.series_id,
            "series_name": self.series_name,
            "sector": self.sector.value,
            "unit": self.unit,
            "current_value": self.current_value,
            "current_period": self.current_period,
            "rate_of_change": {
                "12_12": self.rate_12_12,
                "3_12": self.rate_3_12,
                "1_12": self.rate_1_12
            },
            "business_cycle": {
                "current_phase": self.current_phase.value if self.current_phase else None,
                "forecast_phases": {str(k): v.value if isinstance(v, BusinessPhase) else v
                                   for k, v in self.forecast_phases.items()}
            },
            "forecasts": [f.to_dict() for f in self.forecasts],
            "forecast_table": self.forecast_table.to_dict() if self.forecast_table else None,
            "charts": [c.to_dict() for c in self.charts],
            "content": {
                "overview": self.overview_text,
                "highlights": self.highlights,
                "management_objective": self.management_objective,
                "data_trend_description": self.data_trend_description
            },
            "at_a_glance": self.at_a_glance_row,
            "source": self.source.to_dict() if self.source else None
        }


class EnhancedITRParser:
    """Enhanced parser for ITR Economics Trends Report PDFs."""

    SERIES_PATTERNS = {
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
        r"ITR Retail Sales Leading Indicator": Sector.CORE,

        r"US Stock Prices|S&P 500": Sector.FINANCIAL,
        r"US Government Long-Term Bond Yields": Sector.FINANCIAL,
        r"US Natural Gas Spot Prices": Sector.FINANCIAL,
        r"US Crude Oil Spot Prices": Sector.FINANCIAL,
        r"US Steel Scrap Producer Price": Sector.FINANCIAL,
        r"US Consumer Price Index": Sector.FINANCIAL,
        r"US Producer Price Index": Sector.FINANCIAL,

        r"US Single-Unit Housing Starts": Sector.CONSTRUCTION,
        r"US Multi-Unit Housing Starts": Sector.CONSTRUCTION,
        r"US Private Office Construction": Sector.CONSTRUCTION,
        r"US Total Education Construction": Sector.CONSTRUCTION,
        r"US Total Hospital Construction": Sector.CONSTRUCTION,
        r"US Private Manufacturing Construction": Sector.CONSTRUCTION,
        r"US Private Multi-Tenant Retail Construction": Sector.CONSTRUCTION,
        r"US Private Warehouse Construction": Sector.CONSTRUCTION,
        r"US Public Water.*Sewer.*Construction": Sector.CONSTRUCTION,

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

    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path)
        self.doc = None
        self.report_period = None
        self.extraction_timestamp = datetime.now()
        self.at_a_glance_data = {}  # Cached At-a-Glance data

    def open(self):
        """Open the PDF document."""
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        self.doc = fitz.open(self.pdf_path)
        self._detect_report_period()
        self._extract_at_a_glance_tables()

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

    def _extract_at_a_glance_tables(self):
        """Extract At-a-Glance summary tables from the document."""
        if not self.doc:
            return

        for page_num in range(len(self.doc)):
            text = self.doc[page_num].get_text()
            if "At-a-Glance" in text and "PHASE KEY" in text:
                self._parse_at_a_glance_page(page_num, text)

    def _parse_at_a_glance_page(self, page_num: int, text: str):
        """Parse an At-a-Glance summary page."""
        # Determine sector
        sector = None
        if "Core" in text[:100]:
            sector = Sector.CORE
        elif "Financial" in text[:100]:
            sector = Sector.FINANCIAL
        elif "Construction" in text[:100]:
            sector = Sector.CONSTRUCTION
        elif "Manufacturing" in text[:100]:
            sector = Sector.MANUFACTURING

        if not sector:
            return

        # Extract summary text
        summary_match = re.search(r"SUMMARY\s*\n(.+?)(?=Phase A:|$)", text, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""

        self.at_a_glance_data[sector] = {
            "page": page_num + 1,
            "summary": summary,
            "sector": sector.value
        }

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
            r"Index,\s*\d{4}\s*=\s*\d+,?\s*NSA",
            r"Index,\s*\d{4}-?\d*\s*=\s*\d+",
            r"Billions of Dollars,?\s*NSA",
            r"Billions of Dollars",
            r"Millions of (?:Units|Employees),?\s*NSA",
            r"Millions of (?:Units|Employees)",
            r"Thousands of Units,?\s*NSA",
            r"Thousands of Units",
            r"Trillions of Dollars,?\s*NSA",
            r"Trillions of Dollars",
            r"Percent,?\s*NSA",
            r"Percent",
            r"Dollars per (?:Barrel|MMBtu),?\s*NSA",
            r"Dollars per (?:Barrel|MMBtu)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return "Unknown"

    def _extract_charts_metadata(self, page, page_num: int, series_name: str) -> list[ChartMetadata]:
        """Extract metadata about charts on the page."""
        charts = []
        images = page.get_images()

        # ITR pages typically have 2-3 images: Rate-of-Change chart, Data Trend chart, sometimes Overview
        chart_types = ["rate_of_change", "data_trend", "overview"]

        for i, img in enumerate(images):
            xref, _, width, height = img[0], img[1], img[2], img[3]

            chart_type = chart_types[i] if i < len(chart_types) else f"chart_{i+1}"

            charts.append(ChartMetadata(
                chart_type=chart_type,
                title=f"{series_name} - {chart_type.replace('_', ' ').title()}",
                image_xref=xref,
                width=width,
                height=height,
                page_number=page_num + 1
            ))

        return charts

    def _extract_forecast_table(self, page, text: str, series_name: str) -> Optional[TableData]:
        """Extract the forecast table data with positioning."""
        blocks = page.get_text('dict')['blocks']

        # Find forecast-related text blocks by position
        forecast_items = []
        for block in blocks:
            if 'lines' not in block:
                continue
            for line in block['lines']:
                for span in line['spans']:
                    txt = span['text'].strip()
                    bbox = span['bbox']
                    if txt and any(x in txt for x in ['2024', '2025', '2026', '2027', '12/12', '12MMA', '12MMT', '3MMA', '%', 'FORECAST']):
                        forecast_items.append({
                            'text': txt,
                            'x': bbox[0],
                            'y': bbox[1]
                        })

        if not forecast_items:
            return None

        # Group by Y position to reconstruct table rows
        forecast_items.sort(key=lambda x: (round(x['y'] / 10) * 10, x['x']))

        # Parse the forecast structure
        years = []
        metrics = {}

        for item in forecast_items:
            txt = item['text']
            if re.match(r'20\d{2}:', txt):
                years.append(txt.replace(':', ''))
            elif '12/12' in txt or '12MMA' in txt or '12MMT' in txt or '3MMA' in txt:
                continue  # Header
            elif '%' in txt or re.match(r'-?\d+\.?\d*$', txt):
                pass  # Value

        # Build structured forecast data
        rows = []

        # Extract year-by-year forecasts
        year_pattern = r'(2024|2025|2026|2027)'
        rate_pattern = r'(-?\d+\.?\d*)%'
        value_pattern = r'\$?([\d,\.]+)'

        # Find all forecast blocks in text
        forecast_section = text[text.find('FORECAST'):] if 'FORECAST' in text else text

        for year in ['2024', '2025', '2026', '2027']:
            year_idx = forecast_section.find(f'{year}:')
            if year_idx == -1:
                continue

            # Get the next ~100 chars after year marker
            snippet = forecast_section[year_idx:year_idx+150]

            rate_match = re.search(r'(-?\d+\.?\d*)%', snippet)
            value_match = re.search(r'\n\s*\$?([\d,\.]+)\s*\n', snippet)

            if rate_match or value_match:
                rows.append({
                    'year': int(year),
                    'rate_12_12': float(rate_match.group(1)) if rate_match else None,
                    'value': float(value_match.group(1).replace(',', '').replace('$', '')) if value_match else None
                })

        if not rows:
            return None

        return TableData(
            table_type="forecast",
            title=f"{series_name} Forecast",
            headers=["Year", "12/12 Rate", "Value"],
            rows=rows,
            context=self._extract_forecast_context(text),
            page_number=0
        )

    def _extract_forecast_context(self, text: str) -> str:
        """Extract context around the forecast section."""
        # Look for text near FORECAST heading
        match = re.search(r'FORECAST\s*\n(.+?)(?=LINKS|Ask an Analyst|$)', text, re.DOTALL)
        if match:
            return match.group(1).strip()[:500]
        return ""

    def _extract_forecasts_enhanced(self, text: str) -> list[ForecastRange]:
        """Extract forecast data with improved parsing."""
        forecasts = []

        # Look for the forecast section
        forecast_section = ""
        if "FORECAST" in text:
            start = text.find("FORECAST")
            end = text.find("•", start) if "•" in text[start:] else start + 500
            forecast_section = text[start:end]

        # Also check for year labels with data
        for year in [2024, 2025, 2026, 2027]:
            # Pattern 1: Year followed by rate and value on subsequent lines
            pattern1 = rf'{year}:\s*\n?\s*12/12\s*\n?\s*12MM[AT]\s*\n?\s*(-?\d+\.?\d*)%?\s*\n?\s*\$?([\d,\.]+)'
            match1 = re.search(pattern1, text, re.DOTALL)

            # Pattern 2: Year with inline values
            pattern2 = rf'{year}.*?(-?\d+\.?\d*)%.*?\$?([\d,\.]+)'

            # Pattern 3: Simpler - just find values near year markers
            year_idx = text.find(f'{year}:')
            if year_idx > 0:
                snippet = text[year_idx:year_idx+200]

                # Find rate (percentage)
                rate_match = re.search(r'(-?\d+\.?\d*)%', snippet)
                # Find value (number with possible $ and commas)
                val_match = re.search(r'\n\s*\$?([\d,]+\.?\d*)\s*\n', snippet)

                if rate_match:
                    rate_val = float(rate_match.group(1))
                    forecasts.append(ForecastRange(
                        year=year,
                        metric_type="12/12",
                        value_point=rate_val
                    ))

                if val_match:
                    try:
                        val = float(val_match.group(1).replace(',', '').replace('$', ''))
                        forecasts.append(ForecastRange(
                            year=year,
                            metric_type="12MMA",
                            value_point=val
                        ))
                    except ValueError:
                        pass

        return forecasts

    def _extract_overview_text(self, text: str) -> str:
        """Extract the OVERVIEW section text."""
        match = re.search(r'OVERVIEW\s*\n(.+?)(?=DATA TREND|HIGHLIGHTS|$)', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_data_trend_text(self, text: str) -> str:
        """Extract the DATA TREND description."""
        match = re.search(r'DATA TREND\s*\n(.+?)(?=HIGHLIGHTS|$)', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_highlights(self, text: str) -> list[str]:
        """Extract bullet point highlights."""
        highlights = []

        # Find HIGHLIGHTS section
        highlight_section = ""
        if "HIGHLIGHTS" in text:
            start = text.find("HIGHLIGHTS")
            end = min(
                text.find("Ask an Analyst", start) if "Ask an Analyst" in text[start:] else len(text),
                text.find("ITR MANAGEMENT", start) if "ITR MANAGEMENT" in text[start:] else len(text),
                start + 2000
            )
            highlight_section = text[start:end]

        # Extract bullet points
        bullets = re.findall(r'•\s*(.+?)(?=\n•|\nAsk an Analyst|\nITR MANAGEMENT|$)',
                            highlight_section, re.DOTALL)

        for bullet in bullets[:5]:
            cleaned = ' '.join(bullet.split())  # Normalize whitespace
            if len(cleaned) > 20:
                highlights.append(cleaned)

        return highlights

    def _extract_management_objective(self, text: str) -> str:
        """Extract the ITR Management Objective section."""
        match = re.search(
            r'ITR MANAGEMENT OBJECTIVE\s*\n(.+?)(?=\n2\d{3}:|FORECAST|LINKS|$)',
            text, re.DOTALL | re.IGNORECASE
        )
        if match:
            obj_text = match.group(1).strip()
            # Clean up bullet points
            obj_text = re.sub(r'•\s*', '• ', obj_text)
            return ' '.join(obj_text.split())[:500]
        return ""

    def _extract_current_value(self, text: str) -> tuple[Optional[float], Optional[str]]:
        """Extract current value and period."""
        # Look for patterns like "in January was" or "through January"
        patterns = [
            r'(?:in|through)\s+(January|February|March|April|May|June|July|August|September|October|November|December)(?:\s+\d{4})?\s+(?:was|came in|totaled)\s+(?:at\s+)?\$?([\d,\.]+)',
            r'12MMA\s+(?:in|was)\s+\$?([\d,\.]+)',
            r'12MMT\s+(?:in|was|totaled)\s+\$?([\d,\.]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    period = groups[0]
                    value = float(groups[1].replace(',', '').replace('$', ''))
                    return value, period
                elif len(groups) == 1:
                    value = float(groups[0].replace(',', '').replace('$', ''))
                    return value, None

        return None, None

    def _detect_current_phase(self, text: str) -> Optional[BusinessPhase]:
        """Detect current business cycle phase from text."""
        phase_patterns = {
            BusinessPhase.PHASE_A: [r'Phase A', r'Recovery'],
            BusinessPhase.PHASE_B: [r'Phase B', r'Accelerating Growth'],
            BusinessPhase.PHASE_C: [r'Phase C', r'Slowing Growth'],
            BusinessPhase.PHASE_D: [r'Phase D', r'Recession'],
        }

        # Look for explicit phase mentions
        for phase, patterns in phase_patterns.items():
            for pattern in patterns:
                if re.search(rf'(?:in|entered|transitioned to)\s+{pattern}', text, re.IGNORECASE):
                    return phase

        return None

    def extract_series_from_page(self, page_num: int) -> Optional[EnhancedEconomicSeries]:
        """Extract economic series data from a single page."""
        if not self.doc or page_num >= len(self.doc):
            return None

        page = self.doc[page_num]
        text = page.get_text()

        # Skip non-data pages
        if "At-a-Glance" in text or "PHASE KEY" in text:
            return None
        if "Table of Contents" in text:
            return None
        if "Executive Summary" in text and page_num < 5:
            return None

        # Try to identify the series
        series_info = self._extract_series_name(text)
        if not series_info:
            return None

        series_name, sector = series_info

        # Create series ID from name
        series_id = re.sub(r"[^a-zA-Z0-9]", "_", series_name).lower()

        # Extract all data
        current_value, current_period = self._extract_current_value(text)

        series = EnhancedEconomicSeries(
            series_id=series_id,
            series_name=series_name,
            sector=sector,
            unit=self._extract_unit(text),
            current_value=current_value,
            current_period=current_period,
            current_phase=self._detect_current_phase(text),
            forecasts=self._extract_forecasts_enhanced(text),
            forecast_table=self._extract_forecast_table(page, text, series_name),
            charts=self._extract_charts_metadata(page, page_num, series_name),
            overview_text=self._extract_overview_text(text),
            highlights=self._extract_highlights(text),
            management_objective=self._extract_management_objective(text),
            data_trend_description=self._extract_data_trend_text(text),
            at_a_glance_row=self.at_a_glance_data.get(sector),
            source=self._create_source_metadata(page_num + 1)
        )

        return series

    def extract_all_series(self) -> list[EnhancedEconomicSeries]:
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

    def extract_executive_summary(self) -> dict:
        """Extract the executive summary with context."""
        if not self.doc:
            return {}

        for page_num in range(min(10, len(self.doc))):
            text = self.doc[page_num].get_text()
            if "Executive Summary" in text:
                match = re.search(
                    r'Executive Summary\s*\n?\s*BY:\s*(.+?)\n(.+?)(?=\n\n\n|Core\s*/|$)',
                    text, re.DOTALL
                )
                if match:
                    return {
                        "author": match.group(1).strip(),
                        "content": match.group(2).strip(),
                        "page": page_num + 1
                    }
        return {}

    def get_all_at_a_glance(self) -> dict:
        """Get all At-a-Glance summary data."""
        return self.at_a_glance_data

    def get_page_count(self) -> int:
        """Get the total number of pages."""
        return len(self.doc) if self.doc else 0

    def get_report_metadata(self) -> dict:
        """Get report-level metadata."""
        exec_summary = self.extract_executive_summary()
        return {
            "pdf_filename": self.pdf_path.name,
            "report_period": self.report_period,
            "page_count": self.get_page_count(),
            "extraction_timestamp": self.extraction_timestamp.isoformat(),
            "executive_summary": exec_summary,
            "at_a_glance_pages": {k.value: v["page"] for k, v in self.at_a_glance_data.items()}
        }
