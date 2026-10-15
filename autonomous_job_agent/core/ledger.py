"""Application Ledger: Tracks discovered jobs, submitted applications, statuses, and follow-ups."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table

from autonomous_job_agent.core.config import config


class ApplicationLedger:
    """Persistent ledger tracking all job applications and recruiter responses."""

    def __init__(self):
        self.ledger_file = config.storage_path / "application_ledger.json"
        self._ensure_file()

    def _ensure_file(self):
        if not self.ledger_file.exists():
            self._save_data({"applications": []})

    def _load_data(self) -> Dict:
        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"applications": []}

    def _save_data(self, data: Dict):
        with open(self.ledger_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def record_entry(
        self,
        job_id: str,
        company_name: str,
        job_title: str,
        job_url: str,
        relevance_score: float,
        status: str,
        confirmation_id: str,
        artifacts_dir: Optional[str] = None
    ) -> Dict:
        """Add or update an application tracking record."""
        data = self._load_data()
        apps = data.get("applications", [])

        # Check if already present
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        existing = next((a for a in apps if a.get("job_url") == job_url), None)

        if existing:
            existing["status"] = status
            existing["last_updated"] = now_iso
            existing["confirmation_id"] = confirmation_id
            existing["relevance_score"] = relevance_score
            entry = existing
        else:
            entry = {
                "job_id": job_id,
                "company_name": company_name,
                "job_title": job_title,
                "job_url": job_url,
                "relevance_score": relevance_score,
                "status": status,
                "confirmation_id": confirmation_id,
                "applied_date": now_iso,
                "last_updated": now_iso,
                "followup_t7_date": "",
                "artifacts_dir": artifacts_dir or ""
            }
            apps.append(entry)

        data["applications"] = apps
        self._save_data(data)
        return entry

    @staticmethod
    def classify_entry(app: Dict) -> Dict:
        """Accurately classifies delivery status between live ATS delivery, dry-run staging, and interview states."""
        status = str(app.get("status", "")).upper()
        conf_id = str(app.get("confirmation_id", "")).upper()

        if status in ("INTERVIEW_SCHEDULED", "INTERVIEWING"):
            tier = "INTERVIEW"
            label = "INTERVIEW SCHEDULED"
            badge = "badge-interview"
        elif status in ("OFFER", "OFFER_RECEIVED"):
            tier = "OFFER"
            label = "OFFER RECEIVED"
            badge = "badge-offer"
        elif status == "FOLLOW_UP_SENT":
            tier = "FOLLOW_UP"
            label = "FOLLOW-UP SENT"
            badge = "badge-followup"
        elif status == "REJECTED":
            tier = "REJECTED"
            label = "REJECTED"
            badge = "badge-rejected"
        elif "PAUSED" in status or "HITL" in status or "QUESTION" in status:
            tier = "PAUSED"
            label = "PAUSED (Screening Questions)"
            badge = "badge-paused"
        elif status == "FAILED":
            tier = "FAILED"
            label = "FAILED (Blocked by ATS)"
            badge = "badge-failed"
        elif "DRYRUN" in conf_id or "ASSERTION" in conf_id or status in ("QUEUED", "STAGED", "DRY_RUN"):
            tier = "DRY_RUN"
            label = "STAGED (Pre-flight Dry-Run)"
            badge = "badge-staged"
        elif status in ("SUBMITTED", "APPLIED") or "CONF-" in conf_id or "ATS-" in conf_id:
            tier = "LIVE"
            label = "DELIVERED (Live to ATS)"
            badge = "badge-delivered"
        else:
            tier = "OTHER"
            label = status or "UNKNOWN"
            badge = "badge-staged"

        return {
            "tier": tier,
            "label": label,
            "badge": badge,
            "is_live": tier == "LIVE",
            "is_staged": tier == "DRY_RUN",
            "is_interview": tier == "INTERVIEW",
            "is_paused": tier == "PAUSED",
            "is_followup": tier == "FOLLOW_UP",
        }

    def update_application(
        self,
        job_url_or_id: str,
        new_status: str,
        notes: str = "",
        interview_date: str = "",
        interview_time: str = "",
        interview_round: str = "",
        meeting_link: str = ""
    ) -> Optional[Dict]:
        """Update application status, interview schedules, and recruiter notes."""
        data = self._load_data()
        updated_entry = None
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        for app in data.get("applications", []):
            if app.get("job_url") == job_url_or_id or app.get("job_id") == job_url_or_id:
                app["status"] = new_status
                app["last_updated"] = now_iso
                if notes:
                    app["notes"] = notes
                if interview_date:
                    app["interview_date"] = interview_date
                if interview_time:
                    app["interview_time"] = interview_time
                if interview_round:
                    app["interview_round"] = interview_round
                if meeting_link:
                    app["meeting_link"] = meeting_link
                updated_entry = app
                break

        if updated_entry:
            self._save_data(data)
        return updated_entry

    def record_followup(self, job_url_or_id: str, cadence: str, notes: str = "") -> Optional[Dict]:
        """Record a follow-up action sent to a recruiter."""
        data = self._load_data()
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        updated_entry = None

        for app in data.get("applications", []):
            if app.get("job_url") == job_url_or_id or app.get("job_id") == job_url_or_id:
                app["status"] = "FOLLOW_UP_SENT"
                app["last_updated"] = now_iso
                app["last_followup_at"] = now_iso
                app["last_followup_cadence"] = cadence
                history = app.get("followup_history", [])
                history.append({
                    "timestamp": now_iso,
                    "cadence": cadence,
                    "notes": notes
                })
                app["followup_history"] = history
                updated_entry = app
                break

        if updated_entry:
            self._save_data(data)
        return updated_entry

    def update_status(self, job_url: str, new_status: str, notes: str = ""):
        """Update status e.g. INTERVIEW_SCHEDULED, REJECTED, OFFER."""
        return self.update_application(job_url, new_status, notes=notes)

    def list_all(self) -> List[Dict]:
        return self._load_data().get("applications", [])

    def display_tracker_table(self):
        """Displays rich terminal table with tracking metrics."""
        console = Console()
        apps = self.list_all()

        if not apps:
            console.print("[yellow]No applications tracked yet. Run the auto-scout or pipeline to add applications.[/yellow]")
            return

        table = Table(title="Autonomous Job Application Tracker & Status Ledger", show_lines=True)
        table.add_column("Company", style="cyan", width=18)
        table.add_column("Job Title", style="white", width=25)
        table.add_column("Fit Score", style="magenta", width=10)
        table.add_column("Delivery Status", style="bold", width=22)
        table.add_column("Receipt ID / Error", style="yellow", width=22)
        table.add_column("Date", style="dim", width=12)

        for a in apps:
            fit_pct = f"{a.get('relevance_score', 0):.1%}"
            status = a.get("status", "UNKNOWN")
            conf_id = a.get("confirmation_id", "")
            
            if status == "FAILED":
                disp_status = "[bold red]FAILED (Blocked by ATS)[/bold red]"
                disp_receipt = "[red]HTTP 405 / CSRF Block[/red]"
            elif "DRYRUN" in conf_id or status == "QUEUED":
                disp_status = "[bold cyan]STAGED (Dry-Run)[/bold cyan]"
                disp_receipt = conf_id
            elif status == "SUBMITTED":
                disp_status = "[bold green]DELIVERED (Live)[/bold green]"
                disp_receipt = conf_id
            else:
                disp_status = f"[yellow]{status}[/yellow]"
                disp_receipt = conf_id

            table.add_row(
                a.get("company_name", "Unknown"),
                a.get("job_title", "Unknown"),
                fit_pct,
                disp_status,
                disp_receipt,
                a.get("applied_date", "")[:10]
            )

        console.print(table)


ledger = ApplicationLedger()
