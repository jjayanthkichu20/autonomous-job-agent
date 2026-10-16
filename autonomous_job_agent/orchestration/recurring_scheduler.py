"""Recurring 2-Hour Job Hunter Daemon: Runs continuous background discovery, review, and auto-apply."""

import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional

from autonomous_job_agent.core.config import config
from autonomous_job_agent.core.ledger import ledger
from autonomous_job_agent.core.models import CandidateMasterProfile
from autonomous_job_agent.orchestration.auto_scout import AutoScoutEngine
from autonomous_job_agent.orchestration.pipeline import AutonomousJobApplicationPipeline

logger = logging.getLogger("recurring_scheduler")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATE_FILE = BASE_DIR / "storage" / "scheduler_state.json"


class RecurringJobHunter:
    """Manages continuous 2-hour cycle execution for job scouting, review, tailoring, and application."""

    def __init__(self, interval_seconds: int = 7200):
        self.interval_seconds = interval_seconds  # Default 2 hours (7200 seconds)
        self.is_active = True
        self.is_running_cycle = False
        self.live_submit = True
        self.max_apps_per_cycle = 5
        self.min_auto_apply_score = 0.70
        self.min_stage_draft_score = 0.55
        self.pipeline = AutonomousJobApplicationPipeline()
        self.scout = AutoScoutEngine()
        self._bg_task: Optional[asyncio.Task] = None
        self._load_state()

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.is_active = data.get("is_active", True)
                    self.live_submit = data.get("live_submit", True)
                    self.interval_seconds = data.get("interval_seconds", 7200)
                    self.last_run = data.get("last_run")
                    self.next_run = data.get("next_run")
                    self.total_scans = data.get("total_scans", 0)
                    self.total_applied = data.get("total_applied", 0)
                    self.recent_logs = data.get("recent_logs", [])
                    return
            except Exception as e:
                logger.warning(f"Could not load scheduler state: {e}")

        # Defaults
        self.last_run = None
        self.next_run = (datetime.now(timezone.utc) + timedelta(seconds=self.interval_seconds)).isoformat()
        self.total_scans = 0
        self.total_applied = 0
        self.recent_logs = []
        self._save_state()

    def _save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "is_active": self.is_active,
            "live_submit": self.live_submit,
            "interval_seconds": self.interval_seconds,
            "interval_hours": round(self.interval_seconds / 3600, 1),
            "last_run": self.last_run,
            "next_run": self.next_run,
            "total_scans": self.total_scans,
            "total_applied": self.total_applied,
            "recent_logs": self.recent_logs[-20:],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_profile(self) -> CandidateMasterProfile:
        p1 = BASE_DIR / "my_profile.json"
        p2 = BASE_DIR / "sample_candidate_profile.json"
        target = p1 if p1.exists() else p2
        with open(target, "r", encoding="utf-8") as f:
            return CandidateMasterProfile(**json.load(f))

    def run_cycle(
        self,
        max_applications: Optional[int] = None,
        location_filters: Optional[List[str]] = None,
        max_age_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """Executes a single 2-hour scan, evaluation, auto-apply, and draft staging cycle."""
        if self.is_running_cycle:
            return {"status": "skipped", "message": "Cycle already in progress"}

        self.is_running_cycle = True
        start_time = datetime.now(timezone.utc)
        logger.info(f"=== Starting 2-Hour Autonomous Job Hunt Cycle at {start_time.isoformat()} ===")

        scanned_count = 0
        applied_count = 0
        staged_drafts_count = 0
        cycle_details = []
        app_limit = max_applications if max_applications is not None else self.max_apps_per_cycle

        try:
            profile = self.get_profile()
            locs = location_filters or getattr(profile, "preferred_locations", [])
            discovered = self.scout.search_and_filter_jobs(
                profile=profile,
                location_filters=locs,
                max_age_hours=max_age_hours
            )
            scanned_count = len(discovered)
            
            # Filter already applied
            already_applied_urls = {a.get("job_url") for a in ledger._load_data().get("applications", [])}
            unapplied = [j for j in discovered if j.get("url") not in already_applied_urls]

            for item in unapplied:
                if applied_count >= app_limit:
                    break

                url = item.get("url")
                title = item.get("title", "HR Opening")
                company = item.get("board", "Company").title()

                try:
                    # Ingest and evaluate
                    job = self.pipeline.scraper.fetch_job(url)
                    relevance = self.pipeline.scorer.evaluate(job, profile)
                    score = relevance.overall_score

                    if score >= self.min_auto_apply_score:
                        # Auto-Apply: High Match
                        variant = self.pipeline.tailor.tailor(profile, job, relevance)
                        artifacts = self.pipeline.doc_gen.save_artifacts(profile, job, variant)
                        mappings = self.pipeline.executor.map_form_fields(
                            html_content=job.raw_html or job.raw_description,
                            profile=profile,
                            variant=variant,
                            resume_file_path=artifacts["markdown_path"]
                        )
                        submission = self.pipeline.executor.execute_submission(
                            job=job,
                            profile=profile,
                            variant=variant,
                            field_mappings=mappings,
                            dry_run=not self.live_submit
                        )
                        ledger.record_entry(
                            job_id=job.id,
                            company_name=job.company_name,
                            job_title=job.job_title,
                            job_url=job.canonical_url,
                            relevance_score=score,
                            status=submission.state.value,
                            confirmation_id=submission.external_confirmation_id,
                            artifacts_dir=artifacts["markdown_path"]
                        )
                        applied_count += 1
                        cycle_details.append({
                            "title": title,
                            "company": company,
                            "score": f"{score:.1%}",
                            "action": "AUTO_APPLIED",
                            "confirmation_id": submission.external_confirmation_id
                        })
                        time.sleep(1.0)

                    elif score >= self.min_stage_draft_score:
                        # Stage in Drafts for User Review
                        variant = self.pipeline.tailor.tailor(profile, job, relevance)
                        artifacts = self.pipeline.doc_gen.save_artifacts(profile, job, variant)
                        staged_drafts_count += 1
                        ledger.record_entry(
                            job_id=job.id,
                            company_name=job.company_name,
                            job_title=job.job_title,
                            job_url=job.canonical_url,
                            relevance_score=score,
                            status="DRAFT",
                            confirmation_id=f"DRAFT_STAGED_{variant.sha256_fingerprint[:8]}",
                            artifacts_dir=artifacts["markdown_path"]
                        )
                        cycle_details.append({
                            "title": title,
                            "company": company,
                            "score": f"{score:.1%}",
                            "action": "STAGED_DRAFT",
                            "artifacts_dir": artifacts["markdown_path"]
                        })

                except Exception as ex:
                    logger.warning(f"Error evaluating {url}: {ex}")

        except Exception as e:
            logger.error(f"Error in job hunt cycle: {e}")
        finally:
            self.is_running_cycle = False

        finish_time = datetime.now(timezone.utc)
        self.last_run = finish_time.isoformat()
        self.next_run = (finish_time + timedelta(seconds=self.interval_seconds)).isoformat()
        self.total_scans += scanned_count
        self.total_applied += applied_count

        log_summary = {
            "timestamp": finish_time.isoformat(),
            "scanned": scanned_count,
            "applied": applied_count,
            "staged_drafts": staged_drafts_count,
            "details": cycle_details
        }
        self.recent_logs.append(log_summary)
        self._save_state()

        logger.info(f"=== Completed 2-Hour Cycle: Scanned {scanned_count}, Applied {applied_count}, Staged {staged_drafts_count} ===")
        return log_summary

    async def start_async_loop(self):
        """Asynchronous background loop for continuous 2-hour execution."""
        logger.info(f"RecurringJobHunter background worker started (Interval: {self.interval_seconds}s / {self.interval_seconds // 3600}h)")
        while True:
            try:
                if self.is_active:
                    now = datetime.now(timezone.utc)
                    # Check if next_run is due
                    is_due = True
                    if self.next_run:
                        try:
                            due_dt = datetime.fromisoformat(self.next_run)
                            if now < due_dt:
                                is_due = False
                        except Exception:
                            is_due = True

                    if is_due:
                        # Run cycle in thread pool so it does not block the async event loop
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, self.run_cycle)
            except Exception as e:
                logger.error(f"Error in scheduler background loop: {e}")

            # Sleep 30 seconds between checks
            await asyncio.sleep(30)


# Global singleton instance
recurring_hunter = RecurringJobHunter(interval_seconds=7200)
