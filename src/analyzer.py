"""
Analysis and reporting for ITR Economics data.

Per Constitution Principle V (Visualization Integrity):
- Accurate representation of underlying data
- Proper axis scales and time series intervals
- Clear distinction between historical and forecast data
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import EconomicSeries, Sector, BusinessPhase


class ITRAnalyzer:
    """Analyzer for ITR Economics extracted data."""

    # Phase colors per ITR standard
    PHASE_COLORS = {
        BusinessPhase.PHASE_A: "#4CAF50",  # Green - Recovery
        BusinessPhase.PHASE_B: "#2196F3",  # Blue - Accelerating Growth
        BusinessPhase.PHASE_C: "#FF9800",  # Orange - Slowing Growth
        BusinessPhase.PHASE_D: "#F44336",  # Red - Recession
    }

    def __init__(self, series_list: list[EconomicSeries]):
        self.series_list = series_list

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

    def get_series_with_forecasts(self) -> list[EconomicSeries]:
        """Get series that have forecast data."""
        return [s for s in self.series_list if s.forecasts]

    def get_series_by_phase(self, phase: BusinessPhase) -> list[EconomicSeries]:
        """Get series currently in a specific business cycle phase."""
        return [s for s in self.series_list if s.current_phase == phase]

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """
        Generate a text report of extracted data.

        Args:
            output_path: Optional path to save the report.

        Returns:
            The report as a string.
        """
        lines = []
        lines.append("=" * 80)
        lines.append("ITR ECONOMICS DATA EXTRACTION REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total Series Extracted: {len(self.series_list)}")
        lines.append("")

        # Summary by sector
        lines.append("-" * 40)
        lines.append("SERIES BY SECTOR")
        lines.append("-" * 40)
        for sector, count in self.count_by_sector().items():
            lines.append(f"  {sector.upper()}: {count} series")
        lines.append("")

        # Detailed listing
        for sector in Sector:
            sector_series = [s for s in self.series_list if s.sector == sector]
            if not sector_series:
                continue

            lines.append("-" * 40)
            lines.append(f"{sector.value.upper()} SECTOR")
            lines.append("-" * 40)

            for series in sector_series:
                lines.append(f"\n  {series.series_name}")
                lines.append(f"    Unit: {series.unit}")

                if series.source:
                    lines.append(f"    Source: {series.source.pdf_filename}, Page {series.source.page_number}")

                if series.forecasts:
                    lines.append("    Forecasts:")
                    for forecast in series.forecasts[:6]:  # Limit display
                        if forecast.value_point is not None:
                            lines.append(
                                f"      {forecast.year} ({forecast.metric_type}): "
                                f"{forecast.value_point}"
                            )

                if series.highlights:
                    lines.append("    Key Points:")
                    for highlight in series.highlights[:3]:
                        # Truncate long highlights
                        if len(highlight) > 100:
                            highlight = highlight[:100] + "..."
                        lines.append(f"      • {highlight}")

                if series.management_objective:
                    obj = series.management_objective
                    if len(obj) > 150:
                        obj = obj[:150] + "..."
                    lines.append(f"    Management Objective: {obj}")

        lines.append("")
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)

        report = "\n".join(lines)

        if output_path:
            output_path.write_text(report)
            print(f"Report saved to: {output_path}")

        return report

    def export_to_json(self, output_path: Path) -> None:
        """Export all series data to JSON."""
        data = {
            "extraction_timestamp": datetime.now().isoformat(),
            "total_series": len(self.series_list),
            "series_by_sector": self.count_by_sector(),
            "series": [s.to_dict() for s in self.series_list]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"JSON export saved to: {output_path}")

    def export_to_csv(self, output_path: Path) -> None:
        """Export series summary to CSV."""
        import csv

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "Series ID", "Series Name", "Sector", "Unit",
                "Forecast 2024", "Forecast 2025", "Forecast 2026",
                "Source Page", "Report Period"
            ])

            for series in self.series_list:
                # Extract forecast values for 2024, 2025, 2026
                forecasts = {f.year: f.value_point for f in series.forecasts if f.metric_type == "12/12"}

                writer.writerow([
                    series.series_id,
                    series.series_name,
                    series.sector.value,
                    series.unit,
                    forecasts.get(2024, ""),
                    forecasts.get(2025, ""),
                    forecasts.get(2026, ""),
                    series.source.page_number if series.source else "",
                    series.source.report_period if series.source else ""
                ])

        print(f"CSV export saved to: {output_path}")
