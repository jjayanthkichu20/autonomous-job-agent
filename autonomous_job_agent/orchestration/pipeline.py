"""Orchestration Pipeline: Coordinates all four AI agents across the end-to-end application lifecycle."""

from datetime import datetime
from typing import Any, Dict, Optional
from rich.console import Console

from autonomous_job_agent.agents.agent1_scraper.scraper_engine import JobScraperEngine
from autonomous_job_agent.agents.agent1_scraper.relevance_scorer import RelevanceScorer
from autonomous_job_agent.agents.agent2_customizer.tailor_engine import CVTailorEngine
from autonomous_job_agent.agents.agent2_customizer.document_generator import DocumentGenerator
from autonomous_job_agent.agents.agent2_customizer.diff_engine import DiffEngine
from autonomous_job_agent.agents.agent3_executor.executor_engine import ApplicationExecutorEngine
from autonomous_job_agent.agents.agent3_executor.hitl_gateway import HITLGateway
from autonomous_job_agent.agents.agent4_outreach.email_classifier import RecruiterEmailClassifier
from autonomous_job_agent.agents.agent4_outreach.scheduler import OutreachCoordinator
from autonomous_job_agent.core.ledger import ledger
from autonomous_job_agent.core.models import (
    ApplicationState,
    ApplicationSubmission,
    ApplicationVariant,
    CandidateMasterProfile,
    JobPosting,
    RelevanceScore
)


class AutonomousJobApplicationPipeline:
    """End-to-end coordinator managing Agent 1, 2, 3, and 4."""

    def __init__(self):
        self.console = Console()
        self.scraper = JobScraperEngine()
        self.scorer = RelevanceScorer()
        self.tailor = CVTailorEngine()
        self.doc_gen = DocumentGenerator()
        self.executor = ApplicationExecutorEngine()
        self.hitl = HITLGateway()
        self.outreach = OutreachCoordinator()
        self.email_classifier = RecruiterEmailClassifier()

    def execute_for_url(
        self,
        job_url: str,
        profile: CandidateMasterProfile,
        force_manual: bool = False,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Runs the complete coordinated 4-agent workflow on a target job opening."""
        self.console.print(f"\n[bold green]>>> Starting Multi-Agent Pipeline for:[/bold green] {job_url}")

        # STEP 1: Agent 1 - Discover, Parse, and Score Job
        self.console.print("[dim]Agent 1: Fetching and parsing job posting...[/dim]")
        job: JobPosting = self.scraper.fetch_job(job_url)
        relevance: RelevanceScore = self.scorer.evaluate(job, profile)

        self.console.print(
            f"[bold]Agent 1 Result:[/bold] Found '{job.job_title}' at {job.company_name}. "
            f"Fit Score: [bold cyan]{relevance.overall_score:.1%}[/bold cyan] "
            f"(Hard filters: {'PASSED' if relevance.hard_filter_passed else 'FAILED'})"
        )

        if not relevance.hard_filter_passed:
            self.console.print(f"[bold red]Workflow Aborted:[/bold red] {relevance.rationale}")
            return {
                "status": "ABORTED_HARD_FILTER",
                "job": job,
                "relevance": relevance
            }

        # STEP 2: Agent 2 - Grounded Tailoring and ATS Document Synthesis
        self.console.print("[dim]Agent 2: Synthesizing grounded ATS resume variant and cover letter...[/dim]")
        variant: ApplicationVariant = self.tailor.tailor(profile, job, relevance)
        artifact_paths = self.doc_gen.save_artifacts(profile, job, variant)
        self.console.print(f"[bold]Agent 2 Result:[/bold] Generated ATS documents. SHA-256: [cyan]{variant.sha256_fingerprint[:12]}[/cyan]")
        self.console.print(f"  - Markdown: [underline]{artifact_paths['markdown_path']}[/underline]")
        self.console.print(f"  - Typst:    [underline]{artifact_paths['typst_path']}[/underline]")

        # Print explainability diff
        DiffEngine.print_rich_table(variant)

        # STEP 3: Agent 3 - Form Mapping, Pre-Flight Review & Execution
        self.console.print("[dim]Agent 3: Mapping form inputs and verifying against ATS schema...[/dim]")
        field_mappings = self.executor.map_form_fields(
            html_content=job.raw_html or job.raw_description,
            profile=profile,
            variant=variant,
            resume_file_path=artifact_paths["markdown_path"]
        )

        # Display pre-flight summary
        self.hitl.display_preflight_summary(job, relevance, variant, field_mappings)

        # Evaluate Human-In-The-Loop gate
        can_auto_submit, gate_reason = self.hitl.evaluate_submission_gate(
            job=job,
            relevance=relevance,
            variant=variant,
            mappings=field_mappings,
            force_manual=force_manual
        )
        self.console.print(f"[bold yellow]HITL Gateway Decision:[/bold yellow] {'AUTO-APPROVE' if can_auto_submit else 'MANUAL APPROVAL REQUIRED'}")
        self.console.print(f"  [dim]Rationale: {gate_reason}[/dim]")

        # Execute submission (in safe dry_run or live)
        submission: ApplicationSubmission = self.executor.execute_submission(
            job=job,
            profile=profile,
            variant=variant,
            field_mappings=field_mappings,
            dry_run=dry_run
        )
        self.console.print(
            f"[bold]Agent 3 Result:[/bold] Status: [bold green]{submission.state.value}[/bold green], "
            f"Confirmation: [cyan]{submission.external_confirmation_id}[/cyan]"
        )

        # STEP 4: Agent 4 - Queuing Follow-Up and Tracking Schedules
        followup_preview = self.outreach.generate_followup_message(profile, job, cadence_stage="T+7")
        self.console.print(f"[bold]Agent 4 Result:[/bold] Prepared T+7 follow-up cadence.")

        # Record into Persistent Ledger
        ledger.record_entry(
            job_id=job.id,
            company_name=job.company_name,
            job_title=job.job_title,
            job_url=job.canonical_url,
            relevance_score=relevance.overall_score,
            status=submission.state.value,
            confirmation_id=submission.external_confirmation_id or "DRYRUN",
            artifacts_dir=artifact_paths.get("markdown_path", "")
        )

        return {
            "status": "SUCCESS",
            "job": job,
            "relevance": relevance,
            "variant": variant,
            "artifacts": artifact_paths,
            "submission": submission,
            "followup_template": followup_preview
        }
