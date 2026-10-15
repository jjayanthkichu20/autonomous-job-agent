"""Interactive CLI interface for the Autonomous Multi-Agent Suite."""

import argparse
import json
from pathlib import Path
import sys
import time
from rich.console import Console
from rich.panel import Panel

from autonomous_job_agent.core.models import CandidateMasterProfile
from autonomous_job_agent.mock_ats.server import MockATSServer
from autonomous_job_agent.orchestration.pipeline import AutonomousJobApplicationPipeline
from autonomous_job_agent.agents.agent4_outreach.email_classifier import RecruiterEmailClassifier
from autonomous_job_agent.core.ledger import ledger
from autonomous_job_agent.orchestration.auto_scout import AutoScoutEngine
from autonomous_job_agent.verification import run_formal_verification_test


console = Console()

def load_profile(path_str: str) -> CandidateMasterProfile:
    path = Path(path_str)
    if not path.exists():
        console.print(f"[bold red]Profile file not found at:[/bold red] {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return CandidateMasterProfile(**data)


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Multi-Agent Job Application Suite CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: run-mock-e2e
    subparsers.add_parser(
        "run-mock-e2e",
        help="Start synthetic ATS server and run complete 4-agent pipeline end-to-end"
    )

    # Command: pipeline
    pipe_parser = subparsers.add_parser("pipeline", help="Run 4-agent pipeline against a live URL")
    pipe_parser.add_argument("--url", required=True, help="Job posting URL")
    pipe_parser.add_argument("--profile", default="sample_candidate_profile.json", help="Path to profile JSON")
    pipe_parser.add_argument("--force-manual", action="store_true", help="Force HITL manual approval")
    pipe_parser.add_argument("--live-submit", action="store_true", help="Execute real POST submission (default is dry-run)")

    # Command: tracker
    subparsers.add_parser("tracker", help="Display all tracked job applications and statuses")

    # Command: auto-scout
    scout_parser = subparsers.add_parser("auto-scout", help="Automatically discover and apply to matching jobs")
    scout_parser.add_argument("--profile", default="my_profile.json", help="Path to profile JSON")
    scout_parser.add_argument("--max-apps", type=int, default=3, help="Max applications to process per run")
    scout_parser.add_argument("--live-submit", action="store_true", help="Submit live instead of dry-run")
    scout_parser.add_argument("--boards", nargs="+", default=None, help="Specific company boards to scout")

    # Command: verify
    verify_parser = subparsers.add_parser("verify", help="Run formal 6-phase system audit and live submission test")
    verify_parser.add_argument("--profile", default="my_profile.json", help="Path to profile JSON")

    # Command: recurring
    rec_parser = subparsers.add_parser("recurring", help="Run continuous 2-hour autonomous job hunter daemon")
    rec_parser.add_argument("--interval", type=float, default=2.0, help="Interval in hours (default: 2.0)")
    rec_parser.add_argument("--live-submit", action="store_true", help="Execute live applications instead of dry-run")
    rec_parser.add_argument("--once", action="store_true", help="Execute a single cycle and exit (for cron/scheduled tasks)")

    args = parser.parse_args()

    if args.command == "run-mock-e2e":
        console.print(Panel.fit("[bold green]End-to-End Multi-Agent Integration Simulation[/bold green]\nTesting Agent 1, 2, 3, and 4 against Synthetic Greenhouse ATS"))
        server = MockATSServer(port=8765)
        server.start()
        try:
            profile = load_profile("sample_candidate_profile.json")
            pipeline = AutonomousJobApplicationPipeline()
            mock_url = "http://127.0.0.1:8765/greenhouse/job/101"
            
            result = pipeline.execute_for_url(
                job_url=mock_url,
                profile=profile,
                force_manual=False,
                dry_run=True
            )
            
            console.print("\n[bold green]Simulation Completed Successfully![/bold green]")
            console.print(f"Receipt ID: [bold cyan]{result['submission'].external_confirmation_id}[/bold cyan]")
            console.print(f"Artifacts generated in: [bold cyan]{result['artifacts']['markdown_path']}[/bold cyan]\n")
        finally:
            server.stop()

    elif args.command == "pipeline":
        profile = load_profile(args.profile)
        pipeline = AutonomousJobApplicationPipeline()
        try:
            result = pipeline.execute_for_url(
                job_url=args.url,
                profile=profile,
                force_manual=args.force_manual,
                dry_run=not args.live_submit
            )
        except Exception as e:
            console.print(f"\n[bold red][ERROR] Failed to process job posting:[/bold red] {e}\n")
            sys.exit(1)

    elif args.command == "parse-email":
        classifier = RecruiterEmailClassifier()
        sample_body = args.body or (
            "Hi Alex, We were very impressed by your background in eBPF and Go. "
            "We would love to invite you to a 30-minute phone screen with our VP of Infrastructure. "
            "Are you available this Thursday at 2:00 PM EST or Friday at 10:00 AM EST? "
            "You can also schedule directly here: https://calendly.com/techscale-recruiting/alex"
        )
        analysis = classifier.analyze(args.sender, args.subject, sample_body)
        
        console.print("\n[bold cyan]Agent 4 Recruiter Message Classification:[/bold cyan]")
        console.print(f"Sender: {analysis.sender_name} ({analysis.sender_email})")
        console.print(f"Company: {analysis.company_name}")
        console.print(f"Intent: [bold green]{analysis.intent.value}[/bold green]")
        console.print(f"Urgency: [bold red]{analysis.urgency_level}[/bold red]")
        console.print(f"Booking Link Found: [underline]{analysis.booking_link}[/underline]")
        console.print(f"Proposed Slots: {analysis.proposed_slots}")
        console.print(f"Action Summary: {analysis.action_summary}\n")

    elif args.command == "tracker":
        ledger.display_tracker_table()

    elif args.command == "auto-scout":
        profile = load_profile(args.profile)
        scout = AutoScoutEngine()
        scout.run_scout_cycle(
            profile=profile,
            target_boards=args.boards,
            live_submit=args.live_submit,
            max_applications_per_cycle=args.max_apps
        )

    elif args.command == "verify":
        run_formal_verification_test(profile_path=args.profile)

    elif args.command == "recurring":
        import asyncio
        from autonomous_job_agent.orchestration.recurring_scheduler import recurring_hunter
        recurring_hunter.interval_seconds = int(args.interval * 3600)
        recurring_hunter.live_submit = args.live_submit
        if args.once:
            console.print(f"[bold cyan]Executing single 2-hour job hunt cycle (Live: {args.live_submit})...[/bold cyan]")
            res = recurring_hunter.run_cycle()
            console.print(f"[bold green]Cycle complete. Scanned: {res.get('scanned', 0)}, Applied: {res.get('applied', 0)}, Staged: {res.get('staged_drafts', 0)}[/bold green]")
        else:
            console.print(Panel.fit(f"[bold green]2-Hour Autonomous Job Hunter Daemon[/bold green]\nScanning and auto-applying every {args.interval} hours (Live Submit: {args.live_submit})"))
            asyncio.run(recurring_hunter.start_async_loop())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
