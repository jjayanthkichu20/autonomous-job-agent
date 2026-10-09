"""Human-In-The-Loop (HITL) Gateway: Manages approval barriers, pre-flight inspection, and CAPTCHA escalation."""

from typing import List, Optional, Tuple
from rich.console import Console
from rich.table import Table

from autonomous_job_agent.core.config import config
from autonomous_job_agent.core.models import (
    ApplicationState,
    ApplicationVariant,
    FormFieldMapping,
    JobPosting,
    RelevanceScore
)


class HITLGateway:
    """Enforces human-in-the-loop policies to ensure candidate consent and handle anti-bot friction."""

    def __init__(self):
        self.console = Console()

    def evaluate_submission_gate(
        self,
        job: JobPosting,
        relevance: RelevanceScore,
        variant: ApplicationVariant,
        mappings: List[FormFieldMapping],
        force_manual: bool = False
    ) -> Tuple[bool, str]:
        """
        Determines whether application can auto-submit or requires explicit manual sign-off.
        Default policy: Autonomy threshold is 0.95. Below 0.95 requires manual review.
        """
        if force_manual:
            return False, "Manual review explicitly requested by caller."

        if relevance.overall_score >= config.auto_apply_min_relevance:
            # Check if any mapping has low confidence
            low_conf_mappings = [m for m in mappings if m.confidence_score < 0.85]
            if low_conf_mappings:
                return False, f"Relevance is high ({relevance.overall_score:.2f}), but {len(low_conf_mappings)} form fields have low mapping confidence."
            return True, f"Relevance score ({relevance.overall_score:.2f}) meets auto-apply threshold."

        return False, f"Relevance score ({relevance.overall_score:.2f}) is below auto-apply threshold ({config.auto_apply_min_relevance})."

    def display_preflight_summary(
        self,
        job: JobPosting,
        relevance: RelevanceScore,
        variant: ApplicationVariant,
        mappings: List[FormFieldMapping]
    ):
        """Displays rich terminal summary for pre-flight human inspection."""
        self.console.print("\n[bold yellow]" + "=" * 65 + "[/bold yellow]")
        self.console.print(f"[bold cyan]PRE-FLIGHT APPLICATION REVIEW: {job.company_name} — {job.job_title}[/bold cyan]")
        self.console.print("[bold yellow]" + "=" * 65 + "[/bold yellow]")
        self.console.print(f"[bold]Job URL:[/bold] {job.canonical_url}")
        self.console.print(f"[bold]Relevance Fit:[/bold] {relevance.overall_score:.1%} ({relevance.seniority_alignment})")
        self.console.print(f"[bold]Matched Skills:[/bold] {', '.join(relevance.matched_skills)}")
        self.console.print(f"[bold]Tailored Headline:[/bold] {variant.tailored_headline}\n")

        table = Table(title="Form Field Mappings to be Injected", show_lines=True)
        table.add_column("Field Category", style="cyan")
        table.add_column("Selector", style="magenta")
        table.add_column("Mapped Value", style="white")
        table.add_column("Confidence", style="green")

        for m in mappings:
            display_val = m.injected_value if len(m.injected_value) < 45 else m.injected_value[:42] + "..."
            table.add_row(m.field_name, m.selector, display_val, f"{m.confidence_score:.0%}")

        self.console.print(table)

    def trigger_captcha_escalation(self, challenge_type: str, portal_url: str) -> dict:
        """Simulates initiating a remote handover session for candidate to solve CAPTCHA/2FA."""
        session_id = f"vnc_sess_{int(datetime.utcnow().timestamp())}" if 'datetime' in globals() else "vnc_sess_102"
        session_url = f"https://agent.local/sessions/{session_id}?target={portal_url}"

        self.console.print("\n[bold red][ALERT] Anti-Bot Challenge Encountered![/bold red]")
        self.console.print(f"Challenge Type: [bold]{challenge_type}[/bold]")
        self.console.print(f"Candidate Remote Handover URL: [underline cyan]{session_url}[/underline cyan]")
        self.console.print("[yellow]Paused execution. Waiting for candidate to complete challenge and signal resume...[/yellow]\n")

        return {
            "status": "ESCALATED_TO_HUMAN",
            "challenge_type": challenge_type,
            "session_url": session_url
        }
