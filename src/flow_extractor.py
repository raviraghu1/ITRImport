"""
Flow-Based PDF Extractor for ITR Economics Reports.

Extracts content maintaining the natural flow of the PDF document,
preserving context between text, charts, and images for better
LLM understanding and downstream use.

Creates documents in 'ITRextract_Flow' collection.
"""

import base64
import io
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import fitz  # PyMuPDF
from PIL import Image

from .models import Sector, BusinessPhase
from .analysis_generator import AnalysisGenerator


@dataclass
class ContentBlock:
    """A single content block in the PDF flow."""
    block_type: str  # "text", "image", "chart", "table", "heading", "bullet_list"
    content: Any
    page_number: int
    position: Dict[str, float]  # x0, y0, x1, y1
    sequence_number: int  # Order in the document flow

    # LLM interpretations
    interpretation: Optional[str] = None
    summary: Optional[str] = None

    # Metadata
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        # Don't include base64 image data in output (too large)
        content = self.content
        if isinstance(content, dict) and "image_base64" in content:
            content = {k: v for k, v in content.items() if k != "image_base64"}

        return {
            "block_type": self.block_type,
            "content": content,
            "page_number": self.page_number,
            "position": self.position,
            "sequence_number": self.sequence_number,
            "interpretation": self.interpretation,
            "summary": self.summary,
            "metadata": self.metadata
        }


@dataclass
class PageFlow:
    """Complete flow of content from a single page."""
    page_number: int
    page_type: str  # "series", "at_a_glance", "executive_summary", "table_of_contents", "other"
    series_name: Optional[str] = None
    sector: Optional[str] = None

    # Content blocks in reading order
    blocks: List[ContentBlock] = field(default_factory=list)

    # Page-level interpretations
    page_summary: Optional[str] = None
    key_insights: List[str] = field(default_factory=list)

    # Raw text for reference
    raw_text: str = ""

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "page_type": self.page_type,
            "series_name": self.series_name,
            "sector": self.sector,
            "blocks": [b.to_dict() for b in self.blocks],
            "page_summary": self.page_summary,
            "key_insights": self.key_insights,
            "raw_text": self.raw_text
        }


class FlowExtractor:
    """
    Extract PDF content maintaining document flow and context.

    This extractor preserves the reading order of content, captures
    relationships between text and visuals, and uses LLM to generate
    interpretations of charts and images.
    """

    SERIES_PATTERNS = {
        r"US Industrial Production": "core",
        r"US Nondefense Capital Goods New Orders": "core",
        r"US Private Sector Employment": "core",
        r"US Total Retail Sales": "core",
        r"US Wholesale Trade": "core",
        r"ITR Leading Indicator": "core",
        r"US Total Industry Capacity Utilization": "core",
        r"US OECD Leading Indicator": "core",
        r"US ISM PMI": "core",
        r"ITR Retail Sales Leading Indicator": "core",

        r"US Stock Prices|S&P 500": "financial",
        r"US Government.*Bond Yields": "financial",
        r"US Natural Gas Spot Prices": "financial",
        r"US Crude Oil Spot Prices": "financial",
        r"US Steel Scrap Producer Price": "financial",
        r"US Consumer Price Index": "financial",
        r"US Producer Price Index": "financial",

        r"US Single-Unit Housing Starts": "construction",
        r"US Multi-Unit Housing Starts": "construction",
        r"US Private Office Construction": "construction",
        r"US Total Education Construction": "construction",
        r"US Total Hospital Construction": "construction",
        r"US Private Manufacturing Construction": "construction",
        r"US Private.*Retail Construction": "construction",
        r"US Private Warehouse Construction": "construction",
        r"US Public Water.*Sewer.*Construction": "construction",

        r"US Metalworking Machinery": "manufacturing",
        r"US Machinery New Orders": "manufacturing",
        r"US Construction Machinery": "manufacturing",
        r"US Electrical Equipment": "manufacturing",
        r"US Computers.*Electronics": "manufacturing",
        r"US Defense Capital Goods": "manufacturing",
        r"North America Light Vehicle Production": "manufacturing",
        r"US Oil.*Gas Extraction": "manufacturing",
        r"US Mining Production": "manufacturing",
        r"US Chemicals.*Chemical Products": "manufacturing",
        r"US Civilian Aircraft": "manufacturing",
        r"US Medical Equipment": "manufacturing",
        r"US Heavy-Duty Truck": "manufacturing",
        r"US Food Production": "manufacturing",
    }

    def __init__(self, pdf_path: str | Path, llm_extractor=None):
        self.pdf_path = Path(pdf_path)
        self.doc = None
        self.llm = llm_extractor
        self.report_period = None
        self.extraction_timestamp = datetime.now()
        self.sequence_counter = 0

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
            match = re.search(
                r"(January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+(\d{4})",
                text
            )
            if match:
                self.report_period = f"{match.group(1)} {match.group(2)}"
                break

    def _get_next_sequence(self) -> int:
        """Get the next sequence number."""
        self.sequence_counter += 1
        return self.sequence_counter

    def _identify_series(self, text: str) -> Optional[tuple]:
        """Identify the economic series from text."""
        for pattern, sector in self.SERIES_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0), sector
        return None

    def _identify_page_type(self, text: str, page_num: int) -> str:
        """Identify the type of page."""
        if "Table of Contents" in text:
            return "table_of_contents"
        if "Executive Summary" in text and page_num < 5:
            return "executive_summary"
        if "At-a-Glance" in text or "PHASE KEY" in text:
            return "at_a_glance"
        if self._identify_series(text):
            return "series"
        return "other"

    def _extract_text_blocks(self, page, page_num: int) -> List[ContentBlock]:
        """Extract text blocks in reading order."""
        blocks = []
        dict_blocks = page.get_text("dict")["blocks"]

        for block in dict_blocks:
            if block.get("type") == 0:  # Text block
                bbox = block["bbox"]

                # Combine all text in the block
                text_content = ""
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    text_content += line_text + "\n"

                text_content = text_content.strip()
                if not text_content:
                    continue

                # Determine block type based on formatting and content
                block_type = self._classify_text_block(text_content, block)

                blocks.append(ContentBlock(
                    block_type=block_type,
                    content=text_content,
                    page_number=page_num + 1,
                    position={"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
                    sequence_number=self._get_next_sequence(),
                    metadata={
                        "font_size": self._get_avg_font_size(block),
                        "is_bold": self._is_bold(block)
                    }
                ))

        return blocks

    def _classify_text_block(self, text: str, block: dict) -> str:
        """Classify text block type based on content and formatting."""
        # Check for headings
        if self._is_bold(block) and len(text) < 100:
            if any(h in text.upper() for h in ["OVERVIEW", "DATA TREND", "HIGHLIGHTS",
                                                "FORECAST", "MANAGEMENT OBJECTIVE"]):
                return "section_heading"
            if self._get_avg_font_size(block) > 12:
                return "heading"

        # Check for bullet points
        if text.strip().startswith("•") or text.strip().startswith("-"):
            return "bullet_list"

        # Check for forecast data
        if re.search(r"20\d{2}:\s*\n?\s*12/12", text):
            return "forecast_data"

        return "text"

    def _get_avg_font_size(self, block: dict) -> float:
        """Get average font size in block."""
        sizes = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sizes.append(span.get("size", 10))
        return sum(sizes) / len(sizes) if sizes else 10

    def _is_bold(self, block: dict) -> bool:
        """Check if block contains bold text."""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                font = span.get("font", "").lower()
                if "bold" in font or "heavy" in font:
                    return True
        return False

    def _extract_images(self, page, page_num: int) -> List[ContentBlock]:
        """Extract images/charts from page."""
        blocks = []
        images = page.get_images()

        # Standard ITR chart types in order
        chart_types = ["rate_of_change", "data_trend", "overview_chart"]

        for i, img_info in enumerate(images):
            xref = img_info[0]
            width = img_info[2]
            height = img_info[3]

            # Skip very small images (likely icons)
            if width < 50 or height < 50:
                continue

            # Determine chart type
            chart_type = chart_types[i] if i < len(chart_types) else f"chart_{i+1}"

            # Extract image data for LLM interpretation
            image_data = self._extract_image_data(page, xref)

            blocks.append(ContentBlock(
                block_type="chart",
                content={
                    "chart_type": chart_type,
                    "image_xref": xref,
                    "width": width,
                    "height": height,
                    "image_base64": image_data  # For LLM vision if supported
                },
                page_number=page_num + 1,
                position={"x0": 0, "y0": 0, "x1": width, "y1": height},
                sequence_number=self._get_next_sequence(),
                metadata={"chart_index": i}
            ))

        return blocks

    def _extract_image_data(self, page, xref: int) -> Optional[str]:
        """Extract image data as base64 for LLM analysis."""
        try:
            base_image = self.doc.extract_image(xref)
            image_bytes = base_image["image"]
            return base64.b64encode(image_bytes).decode("utf-8")
        except Exception:
            return None

    def _extract_tables(self, page, page_num: int) -> List[ContentBlock]:
        """Extract tabular data from page."""
        blocks = []
        text = page.get_text()

        # Look for forecast tables
        if "FORECAST" in text:
            forecast_data = self._parse_forecast_section(text)
            if forecast_data:
                blocks.append(ContentBlock(
                    block_type="forecast_table",
                    content=forecast_data,
                    page_number=page_num + 1,
                    position={"x0": 0, "y0": 0, "x1": 0, "y1": 0},
                    sequence_number=self._get_next_sequence(),
                    metadata={"table_type": "forecast"}
                ))

        return blocks

    def _parse_forecast_section(self, text: str) -> Optional[Dict]:
        """Parse forecast section into structured data."""
        forecasts = []

        for year in [2024, 2025, 2026, 2027, 2028]:
            year_idx = text.find(f'{year}:')
            if year_idx == -1:
                continue

            snippet = text[year_idx:year_idx+200]

            # Find rate (percentage)
            rate_match = re.search(r'(-?\d+\.?\d*)%', snippet)
            # Find value
            val_match = re.search(r'\n\s*\$?([\d,]+\.?\d*)\s*\n', snippet)

            if rate_match or val_match:
                forecasts.append({
                    "year": year,
                    "rate_12_12": float(rate_match.group(1)) if rate_match else None,
                    "value": float(val_match.group(1).replace(',', '')) if val_match else None
                })

        return {"forecasts": forecasts} if forecasts else None

    def _generate_chart_interpretation(self, chart_block: ContentBlock,
                                        page_text: str, series_name: str) -> dict:
        """Use LLM with vision to interpret a chart."""
        if not self.llm:
            return {
                "description": self._generate_basic_chart_description(chart_block, series_name),
                "trend_direction": None,
                "current_phase": None,
                "confidence": "low"
            }

        chart_type = chart_block.content.get("chart_type", "chart")
        image_base64 = chart_block.content.get("image_base64")

        # Use vision if image is available
        if image_base64:
            try:
                interpretation = self.llm.interpret_chart_with_vision(
                    image_base64=image_base64,
                    series_name=series_name,
                    chart_type=chart_type,
                    context=page_text[:1500]
                )
                return interpretation
            except Exception as e:
                print(f"Vision interpretation failed, falling back to text: {e}")

        # Fallback to text-based interpretation
        prompt = f"""Analyze this {chart_type} chart for "{series_name}" from an ITR Economics Trends Report.

Based on the surrounding context, provide a detailed interpretation including:
1. What the chart shows (metrics, time period)
2. Current trend direction and strength
3. Key inflection points or notable patterns
4. Business cycle phase indication
5. What this means for business planning

Context from the page:
{page_text[:3000]}

Provide a comprehensive but concise interpretation (3-5 sentences)."""

        try:
            interpretation = self.llm._call_llm(
                "You are an expert economic analyst interpreting ITR Economics charts.",
                prompt
            )
            return {
                "description": interpretation,
                "trend_direction": None,
                "current_phase": None,
                "confidence": "medium"
            }
        except Exception as e:
            return {
                "description": self._generate_basic_chart_description(chart_block, series_name),
                "trend_direction": None,
                "current_phase": None,
                "confidence": "low"
            }

    def _generate_basic_chart_description(self, chart_block: ContentBlock, series_name: str) -> str:
        """Generate basic chart description without LLM."""
        chart_type = chart_block.content.get("chart_type", "chart")

        descriptions = {
            "rate_of_change": f"Rate-of-Change chart showing the year-over-year percentage change in {series_name}. "
                             f"This chart displays the 12/12 rate (annual change), 3/12 rate (quarterly change), "
                             f"and 1/12 rate (monthly change) to illustrate momentum and trend direction.",
            "data_trend": f"Data Trend chart showing the actual values of {series_name} over time. "
                         f"Typically displays the 12-month moving average (12MMA) or 12-month moving total (12MMT) "
                         f"to smooth seasonal variations and reveal underlying trends.",
            "overview_chart": f"Overview chart providing a long-term perspective on {series_name}. "
                             f"Shows historical data alongside forecasts to contextualize current conditions "
                             f"within the broader business cycle."
        }

        return descriptions.get(chart_type, f"Chart displaying {series_name} economic data.")

    def _generate_page_summary(self, page_flow: PageFlow) -> str:
        """Generate a summary of the page content."""
        if not self.llm:
            return self._generate_basic_page_summary(page_flow)

        # Collect all text content
        text_content = "\n".join([
            b.content for b in page_flow.blocks
            if b.block_type in ["text", "heading", "bullet_list", "section_heading"]
        ])

        prompt = f"""Summarize this page from an ITR Economics Trends Report about {page_flow.series_name or 'economic data'}.

Content:
{text_content[:4000]}

Provide:
1. A 2-3 sentence summary of the key information
2. The current economic status/phase
3. The outlook/forecast direction
4. Key action items or implications for businesses

Format as a cohesive summary paragraph."""

        try:
            return self.llm._call_llm(
                "You are an expert economic analyst summarizing ITR Economics reports.",
                prompt
            )
        except Exception:
            return self._generate_basic_page_summary(page_flow)

    def _generate_basic_page_summary(self, page_flow: PageFlow) -> str:
        """Generate basic page summary without LLM."""
        if page_flow.series_name:
            return f"Economic series page for {page_flow.series_name} in the {page_flow.sector} sector."
        elif page_flow.page_type == "executive_summary":
            return "Executive Summary providing an overview of current economic conditions and outlook."
        elif page_flow.page_type == "at_a_glance":
            return "At-a-Glance summary showing business cycle phases for multiple economic indicators."
        return f"Page {page_flow.page_number} content."

    def _extract_key_insights(self, page_flow: PageFlow) -> List[str]:
        """Extract key insights from page content."""
        insights = []

        for block in page_flow.blocks:
            # Extract bullet points as insights
            if block.block_type == "bullet_list":
                bullets = [b.strip() for b in block.content.split("•") if b.strip()]
                insights.extend(bullets[:3])

            # Extract highlights section content
            if block.block_type == "section_heading" and "HIGHLIGHT" in block.content.upper():
                # Get the next text block
                idx = page_flow.blocks.index(block)
                if idx + 1 < len(page_flow.blocks):
                    next_block = page_flow.blocks[idx + 1]
                    if next_block.block_type in ["text", "bullet_list"]:
                        bullets = [b.strip() for b in next_block.content.split("•") if b.strip()]
                        insights.extend(bullets[:3])

        return insights[:5]  # Limit to 5 insights

    def extract_page_flow(self, page_num: int) -> PageFlow:
        """Extract content flow from a single page."""
        if not self.doc or page_num >= len(self.doc):
            raise ValueError(f"Invalid page number: {page_num}")

        page = self.doc[page_num]
        text = page.get_text()

        # Identify page type and series
        page_type = self._identify_page_type(text, page_num)
        series_info = self._identify_series(text)
        series_name = series_info[0] if series_info else None
        sector = series_info[1] if series_info else None

        # Create page flow
        page_flow = PageFlow(
            page_number=page_num + 1,
            page_type=page_type,
            series_name=series_name,
            sector=sector,
            raw_text=text
        )

        # Extract all content blocks
        text_blocks = self._extract_text_blocks(page, page_num)
        image_blocks = self._extract_images(page, page_num)
        table_blocks = self._extract_tables(page, page_num)

        # Combine and sort by position (top to bottom, left to right)
        all_blocks = text_blocks + image_blocks + table_blocks
        all_blocks.sort(key=lambda b: (b.position["y0"], b.position["x0"]))

        # Generate interpretations for charts
        for block in all_blocks:
            if block.block_type == "chart":
                interpretation_result = self._generate_chart_interpretation(
                    block, text, series_name or "Unknown Series"
                )
                # Store the full interpretation as metadata
                block.metadata["vision_interpretation"] = interpretation_result
                block.interpretation = interpretation_result.get("description", "")
                block.summary = f"{block.content.get('chart_type', 'Chart')} for {series_name or 'economic data'}"

                # Add trend and phase to metadata
                if interpretation_result.get("trend_direction"):
                    block.metadata["trend_direction"] = interpretation_result["trend_direction"]
                if interpretation_result.get("current_phase"):
                    block.metadata["current_phase"] = interpretation_result["current_phase"]
                if interpretation_result.get("business_implications"):
                    block.metadata["business_implications"] = interpretation_result["business_implications"]
                if interpretation_result.get("key_patterns"):
                    block.metadata["key_patterns"] = interpretation_result["key_patterns"]

        page_flow.blocks = all_blocks

        # Generate page-level summary and insights
        page_flow.page_summary = self._generate_page_summary(page_flow)
        page_flow.key_insights = self._extract_key_insights(page_flow)

        return page_flow

    def extract_full_document_flow(self, generate_analysis: bool = True) -> Dict[str, Any]:
        """Extract the complete document flow.

        Args:
            generate_analysis: If True, generate overall and sector analysis using LLM

        Returns:
            Complete document dictionary with optional analysis
        """
        if not self.doc:
            raise RuntimeError("PDF not opened. Call open() first.")

        pages = []
        series_pages = []
        other_pages = []

        for page_num in range(len(self.doc)):
            page_flow = self.extract_page_flow(page_num)
            pages.append(page_flow)

            if page_flow.page_type == "series":
                series_pages.append(page_flow)
            else:
                other_pages.append(page_flow)

        # Build the complete document
        document = {
            "report_id": self.pdf_path.stem.replace(" ", "_").lower(),
            "pdf_filename": self.pdf_path.name,
            "report_period": self.report_period,
            "extraction_timestamp": self.extraction_timestamp.isoformat(),

            "metadata": {
                "total_pages": len(self.doc),
                "series_pages_count": len(series_pages),
                "total_charts": sum(
                    len([b for b in p.blocks if b.block_type == "chart"])
                    for p in pages
                ),
                "sectors_covered": list(set(p.sector for p in series_pages if p.sector))
            },

            # Document flow - maintains reading order
            "document_flow": [p.to_dict() for p in pages],

            # Series index for quick lookup
            "series_index": {
                p.series_name: {
                    "page_number": p.page_number,
                    "sector": p.sector,
                    "summary": p.page_summary,
                    "insights": p.key_insights
                }
                for p in series_pages if p.series_name
            },

            # Aggregated insights
            "aggregated_insights": self._aggregate_insights(series_pages)
        }

        # Generate analysis if requested
        if generate_analysis:
            analysis_generator = AnalysisGenerator(self.llm)
            analysis_result = analysis_generator.generate_analysis(document)

            # Add analysis fields to document
            document["overall_analysis"] = analysis_result.get("overall_analysis")
            document["sector_analyses"] = analysis_result.get("sector_analyses")
            document["analysis_metadata"] = analysis_result.get("analysis_metadata")

        return document

    def _aggregate_insights(self, series_pages: List[PageFlow]) -> Dict:
        """Aggregate insights across all series pages."""
        all_insights = []
        by_sector = {}

        for page in series_pages:
            all_insights.extend(page.key_insights)

            if page.sector:
                if page.sector not in by_sector:
                    by_sector[page.sector] = []
                by_sector[page.sector].extend(page.key_insights)

        return {
            "total_insights": len(all_insights),
            "by_sector": {k: v[:5] for k, v in by_sector.items()},
            "top_insights": all_insights[:10]
        }


def create_flow_document(pdf_path: Path, llm_extractor=None, verbose: bool = True) -> Dict:
    """
    Create a flow-based document from a PDF.

    Args:
        pdf_path: Path to the PDF file
        llm_extractor: Optional LLM extractor for interpretations
        verbose: Whether to print progress

    Returns:
        Complete flow document as dictionary
    """
    if verbose:
        print(f"Extracting flow document from: {pdf_path.name}")

    with FlowExtractor(pdf_path, llm_extractor) as extractor:
        document = extractor.extract_full_document_flow()

    if verbose:
        print(f"  Pages: {document['metadata']['total_pages']}")
        print(f"  Series: {len(document['series_index'])}")
        print(f"  Charts: {document['metadata']['total_charts']}")

    return document
