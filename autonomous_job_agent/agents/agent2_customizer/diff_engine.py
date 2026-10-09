"""Diff Engine: Formats and exposes explainability diffs between Master Profile and tailored variants."""

from typing import List
from rich.table import Table
from rich.console import Console
from autonomous_job_agent.core.models import ApplicationVariant, BulletDiff


class DiffEngine:
    """Provides transparent explainability for candidate inspection before application submission."""

    @staticmethod
    def generate_text_report(variant: ApplicationVariant) -> str:
        lines = [
            "=" * 70,
            f"EXPLAINABILITY & FACT ATTRIBUTION REPORT (Variant: {variant.id[:8]})",
            "=" * 70,
            f"Tailored Headline: {variant.tailored_headline}",
            "",
            "ATS KEYWORD RELEVANCE DENSITY:",
        ]
        for kw, density in variant.ats_keyword_density.items():
            lines.append(f"  - {kw}: {density:.1%}")
        lines.append("")
        lines.append("FACT-GROUNDED BULLET MODIFICATIONS:")
        lines.append("-" * 70)

        for i, diff in enumerate(variant.bullet_diffs, 1):
            lines.append(f"[{i}] Section: {diff.section}")
            lines.append(f"    Anchored Facts : {', '.join(diff.anchored_fact_ids)}")
            lines.append(f"    Original       : {diff.original_text}")
            lines.append(f"    Tailored (ATS) : {diff.tailored_text}")
            lines.append(f"    Rationale      : {diff.rationale}")
            lines.append("-" * 70)

        return "\n".join(lines)

    @staticmethod
    def print_rich_table(variant: ApplicationVariant):
        """Render a formatted table to terminal using Rich."""
        console = Console()
        table = Table(title=f"CV Tailoring Diff & Fact Grounding ({variant.id[:8]})", show_lines=True)

        table.add_column("Section", style="cyan", width=22)
        table.add_column("Fact Anchor", style="magenta", width=14)
        table.add_column("Original vs Tailored", style="white")
        table.add_column("Rationale", style="green", width=25)

        for diff in variant.bullet_diffs:
            comparison = (
                f"[dim]Orig:[/dim] {diff.original_text}\n\n"
                f"[bold cyan]ATS:[/bold cyan] {diff.tailored_text}"
            )
            table.add_row(
                diff.section,
                ", ".join(diff.anchored_fact_ids),
                comparison,
                diff.rationale
            )

        console.print(table)
