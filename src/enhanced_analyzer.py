"""
Enhanced Analysis and reporting for ITR Economics data.

Per Constitution Principle V (Visualization Integrity):
- Accurate representation of underlying data
- Proper context for charts and tables
- Clear distinction between historical and forecast data
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .enhanced_parser import EnhancedEconomicSeries, ChartMetadata, TableData
from .models import Sector, BusinessPhase


class EnhancedITRAnalyzer:
    """Enhanced analyzer for ITR Economics extracted data."""

    PHASE_DESCRIPTIONS = {
        BusinessPhase.PHASE_A: "Recovery - Economy beginning to grow after a trough",
        BusinessPhase.PHASE_B: "Accelerating Growth - Growth rate increasing, expansion strengthening",
        BusinessPhase.PHASE_C: "Slowing Growth - Still growing but rate declining, approaching peak",
        BusinessPhase.PHASE_D: "Recession - Contraction, declining activity",
    }

    PHASE_COLORS = {
        BusinessPhase.PHASE_A: "#4CAF50",  # Green
        BusinessPhase.PHASE_B: "#2196F3",  # Blue
        BusinessPhase.PHASE_C: "#FF9800",  # Orange
        BusinessPhase.PHASE_D: "#F44336",  # Red
    }

    def __init__(self, series_list: list[EnhancedEconomicSeries], report_metadata: dict = None):
        self.series_list = series_list
        self.report_metadata = report_metadata or {}

    def summary_by_sector(self) -> dict[str, list[str]]:
        """Get a summary of series grouped by sector."""
        summary = {sector.value: [] for sector in Sector}
        for series in self.series_list:
            summary[series.sector.value].append(series.series_name)
        return summary

    def count_by_sector(self) -> dict[str, int]:
        """Count series by sector."""
        counts = {sector.value: 0 for sector in Sector}
        for series in self.series_list:
            counts[series.sector.value] += 1
        return counts

    def get_series_with_forecasts(self) -> list[EnhancedEconomicSeries]:
        """Get series that have forecast data."""
        return [s for s in self.series_list if s.forecasts]

    def get_series_with_charts(self) -> list[EnhancedEconomicSeries]:
        """Get series that have chart metadata."""
        return [s for s in self.series_list if s.charts]

    def get_forecast_summary(self) -> dict:
        """Get a summary of all forecasts by year."""
        summary = {2024: [], 2025: [], 2026: [], 2027: []}

        for series in self.series_list:
            for forecast in series.forecasts:
                if forecast.year in summary and forecast.metric_type == "12/12":
                    summary[forecast.year].append({
                        "series": series.series_name,
                        "sector": series.sector.value,
                        "rate": forecast.value_point
                    })

        return summary

    def generate_detailed_report(self, output_path: Optional[Path] = None) -> str:
        """Generate a detailed report with chart and table context."""
        lines = []

        # Header
        lines.append("=" * 100)
        lines.append("ITR ECONOMICS DATA EXTRACTION REPORT - ENHANCED")
        lines.append("=" * 100)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if self.report_metadata:
            lines.append(f"Source: {self.report_metadata.get('pdf_filename', 'Unknown')}")
            lines.append(f"Report Period: {self.report_metadata.get('report_period', 'Unknown')}")
            lines.append(f"Total Pages: {self.report_metadata.get('page_count', 'Unknown')}")

        lines.append(f"Total Series Extracted: {len(self.series_list)}")
        lines.append("")

        # Executive Summary if available
        if self.report_metadata.get('executive_summary'):
            exec_sum = self.report_metadata['executive_summary']
            lines.append("-" * 50)
            lines.append("EXECUTIVE SUMMARY")
            lines.append("-" * 50)
            if exec_sum.get('author'):
                lines.append(f"Author: {exec_sum['author']}")
            if exec_sum.get('content'):
                content = exec_sum['content'][:1000]
                lines.append(f"\n{content}")
                if len(exec_sum.get('content', '')) > 1000:
                    lines.append("... [truncated]")
            lines.append("")

        # Summary by sector
        lines.append("-" * 50)
        lines.append("SERIES BY SECTOR")
        lines.append("-" * 50)
        for sector, count in self.count_by_sector().items():
            lines.append(f"  {sector.upper()}: {count} series")
        lines.append("")

        # Forecast overview
        forecast_summary = self.get_forecast_summary()
        lines.append("-" * 50)
        lines.append("FORECAST OVERVIEW (12/12 Rate of Change)")
        lines.append("-" * 50)
        for year, forecasts in forecast_summary.items():
            if forecasts:
                lines.append(f"\n  {year}:")
                # Safe sorting with type conversion
                def safe_rate(x):
                    r = x.get('rate')
                    if r is None:
                        return 0
                    try:
                        return float(r)
                    except (ValueError, TypeError):
                        return 0
                for f in sorted(forecasts, key=safe_rate, reverse=True)[:10]:
                    rate = f['rate']
                    try:
                        rate_str = f"{float(rate):+.1f}%" if rate is not None else "N/A"
                    except (ValueError, TypeError):
                        rate_str = str(rate) if rate else "N/A"
                    lines.append(f"    {f['series'][:40]:<42} {rate_str:>8} ({f['sector']})")
        lines.append("")

        # Detailed by sector
        for sector in Sector:
            sector_series = [s for s in self.series_list if s.sector == sector]
            if not sector_series:
                continue

            lines.append("")
            lines.append("=" * 100)
            lines.append(f"{sector.value.upper()} SECTOR")
            lines.append("=" * 100)

            for series in sector_series:
                lines.append("")
                lines.append("-" * 80)
                lines.append(f"  {series.series_name}")
                lines.append("-" * 80)

                # Basic info
                lines.append(f"    Series ID: {series.series_id}")
                lines.append(f"    Unit: {series.unit}")

                if series.source:
                    lines.append(f"    Source: Page {series.source.page_number}")

                # Current value
                if series.current_value:
                    lines.append(f"    Current Value: {series.current_value}")
                    if series.current_period:
                        lines.append(f"    Period: {series.current_period}")

                # Business cycle phase
                if series.current_phase:
                    phase_desc = self.PHASE_DESCRIPTIONS.get(series.current_phase, "")
                    lines.append(f"    Current Phase: {series.current_phase.value} - {phase_desc}")

                # Charts metadata
                if series.charts:
                    lines.append(f"\n    CHARTS ({len(series.charts)} found):")
                    for chart in series.charts:
                        lines.append(f"      • {chart.chart_type.replace('_', ' ').title()}")
                        lines.append(f"        Dimensions: {chart.width}x{chart.height}")

                # Forecast table
                if series.forecast_table and series.forecast_table.rows:
                    lines.append(f"\n    FORECAST TABLE:")
                    lines.append(f"      {'Year':<8} {'12/12 Rate':<12} {'Value':<15}")
                    lines.append(f"      {'-'*8} {'-'*12} {'-'*15}")
                    for row in series.forecast_table.rows:
                        year = row.get('year', '')
                        rate = row.get('rate_12_12')
                        value = row.get('value')
                        rate_str = f"{rate:+.1f}%" if rate is not None else "N/A"
                        value_str = f"{value:,.1f}" if value is not None else "N/A"
                        lines.append(f"      {year:<8} {rate_str:<12} {value_str:<15}")

                    if series.forecast_table.context:
                        lines.append(f"\n      Context: {series.forecast_table.context[:200]}...")

                # Forecasts (alternative format if no table)
                elif series.forecasts:
                    lines.append(f"\n    FORECASTS:")
                    by_year = {}
                    for f in series.forecasts:
                        if f.year not in by_year:
                            by_year[f.year] = {}
                        by_year[f.year][f.metric_type] = f.value_point

                    for year in sorted(by_year.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
                        metrics = by_year[year]
                        rate = metrics.get('12/12')
                        value = metrics.get('12MMA') or metrics.get('12MMT')
                        try:
                            rate_str = f"{float(rate):+.1f}%" if rate is not None else ""
                        except (ValueError, TypeError):
                            rate_str = str(rate) if rate else ""
                        try:
                            value_str = f"{float(value):,.1f}" if value is not None else ""
                        except (ValueError, TypeError):
                            value_str = str(value) if value else ""
                        lines.append(f"      {year}: {rate_str} / {value_str}")

                # Overview
                if series.overview_text:
                    lines.append(f"\n    OVERVIEW:")
                    overview = series.overview_text[:400]
                    lines.append(f"      {overview}")
                    if len(series.overview_text) > 400:
                        lines.append("      ... [truncated]")

                # Highlights
                if series.highlights:
                    lines.append(f"\n    KEY HIGHLIGHTS:")
                    for i, highlight in enumerate(series.highlights[:5], 1):
                        hl = highlight[:150]
                        lines.append(f"      {i}. {hl}")
                        if len(highlight) > 150:
                            lines.append("         ... [truncated]")

                # Management objective
                if series.management_objective:
                    lines.append(f"\n    MANAGEMENT OBJECTIVE:")
                    obj = series.management_objective[:300]
                    lines.append(f"      {obj}")
                    if len(series.management_objective) > 300:
                        lines.append("      ... [truncated]")

                # At-a-Glance context
                if series.at_a_glance_row:
                    lines.append(f"\n    AT-A-GLANCE CONTEXT:")
                    lines.append(f"      Summary Page: {series.at_a_glance_row.get('page', 'N/A')}")
                    if series.at_a_glance_row.get('summary'):
                        summary = series.at_a_glance_row['summary'][:200]
                        lines.append(f"      {summary}...")

        # Footer
        lines.append("")
        lines.append("=" * 100)
        lines.append("END OF REPORT")
        lines.append("=" * 100)

        report = "\n".join(lines)

        if output_path:
            output_path.write_text(report, encoding='utf-8')
            print(f"Detailed report saved to: {output_path}")

        return report

    def export_to_json(self, output_path: Path) -> None:
        """Export all series data to JSON with full context."""
        data = {
            "extraction_timestamp": datetime.now().isoformat(),
            "report_metadata": self.report_metadata,
            "total_series": len(self.series_list),
            "series_by_sector": self.count_by_sector(),
            "forecast_summary": self.get_forecast_summary(),
            "series": [s.to_dict() for s in self.series_list]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        print(f"JSON export saved to: {output_path}")

    def export_to_csv(self, output_path: Path) -> None:
        """Export series summary to CSV."""
        import csv

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "Series ID", "Series Name", "Sector", "Unit",
                "Current Value", "Current Period", "Current Phase",
                "2024 Rate", "2024 Value",
                "2025 Rate", "2025 Value",
                "2026 Rate", "2026 Value",
                "Charts Count", "Has Forecast Table",
                "Source Page", "Report Period"
            ])

            for series in self.series_list:
                # Extract forecast values by year
                forecasts = {}
                for f in series.forecasts:
                    if f.year not in forecasts:
                        forecasts[f.year] = {}
                    if f.metric_type == "12/12":
                        forecasts[f.year]['rate'] = f.value_point
                    elif f.metric_type in ["12MMA", "12MMT"]:
                        forecasts[f.year]['value'] = f.value_point

                writer.writerow([
                    series.series_id,
                    series.series_name,
                    series.sector.value,
                    series.unit,
                    series.current_value or "",
                    series.current_period or "",
                    series.current_phase.value if series.current_phase else "",
                    forecasts.get(2024, {}).get('rate', ""),
                    forecasts.get(2024, {}).get('value', ""),
                    forecasts.get(2025, {}).get('rate', ""),
                    forecasts.get(2025, {}).get('value', ""),
                    forecasts.get(2026, {}).get('rate', ""),
                    forecasts.get(2026, {}).get('value', ""),
                    len(series.charts),
                    "Yes" if series.forecast_table else "No",
                    series.source.page_number if series.source else "",
                    series.source.report_period if series.source else ""
                ])

        print(f"CSV export saved to: {output_path}")

    def export_charts_manifest(self, output_path: Path) -> None:
        """Export a manifest of all charts for reference."""
        charts_data = []

        for series in self.series_list:
            for chart in series.charts:
                charts_data.append({
                    "series_id": series.series_id,
                    "series_name": series.series_name,
                    "sector": series.sector.value,
                    "chart_type": chart.chart_type,
                    "title": chart.title,
                    "dimensions": f"{chart.width}x{chart.height}",
                    "page": chart.page_number,
                    "image_xref": chart.image_xref
                })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_charts": len(charts_data),
                "charts": charts_data
            }, f, indent=2)

        print(f"Charts manifest saved to: {output_path}")

    def export_forecast_tables(self, output_path: Path) -> None:
        """Export all forecast tables to a single JSON file."""
        tables_data = []

        for series in self.series_list:
            if series.forecast_table:
                tables_data.append({
                    "series_id": series.series_id,
                    "series_name": series.series_name,
                    "sector": series.sector.value,
                    "table": series.forecast_table.to_dict()
                })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_tables": len(tables_data),
                "tables": tables_data
            }, f, indent=2)

        print(f"Forecast tables saved to: {output_path}")
