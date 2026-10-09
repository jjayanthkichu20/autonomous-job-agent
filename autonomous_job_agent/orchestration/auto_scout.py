"""Auto-Scout Engine: Resilient discovery across career boards, location-aware matching, and auto-apply."""

import re
import time
from typing import Dict, List, Optional
import requests
from rich.console import Console

from autonomous_job_agent.core.ledger import ledger
from autonomous_job_agent.core.models import CandidateMasterProfile
from autonomous_job_agent.orchestration.pipeline import AutonomousJobApplicationPipeline


DEFAULT_TARGET_BOARDS = [
    "canonical",
    "quince",
    "inmobi",
    "appsflyer",
    "gitlab",
    "springworks",
    "postman",
    "browserstack",
    "razorpay",
    "swiggy",
    "chargebee",
    "airmeet",
    "freshworks"
]


class AutoScoutEngine:
    """Discovers openings across company career boards, filters by location, and triggers the application pipeline."""

    def __init__(self):
        self.console = Console()
        self.pipeline = AutonomousJobApplicationPipeline()

    def discover_jobs_on_greenhouse(self, board_name: str) -> List[Dict]:
        """Queries public Greenhouse API for active postings."""
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_name}/jobs"
        try:
            resp = requests.get(api_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("jobs", [])
        except Exception as e:
            self.console.print(f"[dim red]Error querying board '{board_name}': {e}[/dim red]")
        return []

    def is_location_match(self, job_location: str, allowed_locations: List[str]) -> bool:
        """Checks if a job location satisfies the target location preferences or is remote."""
        if not allowed_locations:
            return True
        
        j_loc = (job_location or "").lower()
        if any(rem in j_loc for rem in ["remote", "anywhere", "worldwide", "distributed", "virtual", "home"]):
            return True
        
        for loc in allowed_locations:
            clean_loc = loc.lower().strip()
            if not clean_loc:
                continue
            if clean_loc in j_loc:
                return True
            # Synonyms
            if clean_loc in ("bangalore", "bengaluru") and any(b in j_loc for b in ["bangalore", "bengaluru"]):
                return True
            if clean_loc in ("kerala", "kottayam", "cochin", "kochi", "trivandrum") and any(k in j_loc for k in ["kerala", "kottayam", "cochin", "kochi", "trivandrum"]):
                return True
            if clean_loc in ("uae", "dubai", "abu dhabi") and any(u in j_loc for u in ["uae", "dubai", "abu dhabi", "emirates"]):
                return True
            if clean_loc == "india" and any(ind in j_loc for ind in ["india", "bangalore", "bengaluru", "mumbai", "delhi", "gurgaon", "noida", "hyderabad", "chennai", "pune", "kerala"]):
                return True
        return False

    def search_and_filter_jobs(
        self,
        profile: CandidateMasterProfile,
        target_boards: Optional[List[str]] = None,
        location_filters: Optional[List[str]] = None,
        keyword_filter: Optional[str] = None
    ) -> List[Dict]:
        """Searches across career boards and returns ranked, location-verified job openings."""
        boards = target_boards or DEFAULT_TARGET_BOARDS
        allowed_locations = location_filters or getattr(profile, "preferred_locations", []) or []
        
        already_applied_urls = {a.get("job_url") for a in ledger._load_data().get("applications", [])}

        target_role_terms = set()
        if keyword_filter and keyword_filter.strip():
            for kw in keyword_filter.lower().split():
                if len(kw) > 2:
                    target_role_terms.add(kw)
        else:
            for r in profile.target_roles:
                for term in r.lower().split():
                    if len(term) > 2:
                        target_role_terms.add(term)
        is_hr_profile = any("hr" in r.lower() or "people" in r.lower() or "talent" in r.lower() for r in profile.target_roles)
        
        discovered = []
        for board in boards:
            raw_jobs = self.discover_jobs_on_greenhouse(board)
            for j in raw_jobs:
                title = j.get("title", "")
                title_lower = title.lower()
                loc_name = j.get("location", {}).get("name", "Remote/Unspecified")
                job_url = j.get("absolute_url")

                # Keyword match
                if is_hr_profile:
                    # Require explicit HR/People/Talent indicator
                    hr_keywords = ["hr", "people", "talent", "recruit", "onboarding", "human resources", "hrms", "payroll", "personnel"]
                    if not any(k in title_lower for k in hr_keywords):
                        continue
                elif target_role_terms and not any(term in title_lower for term in target_role_terms):
                    continue

                # Location match
                loc_matched = self.is_location_match(loc_name, allowed_locations)
                if not loc_matched:
                    continue

                already_applied = job_url in already_applied_urls

                discovered.append({
                    "board": board,
                    "title": title,
                    "location": loc_name,
                    "url": job_url,
                    "already_applied": already_applied,
                    "is_remote": any(r in loc_name.lower() for r in ["remote", "anywhere", "worldwide"]),
                    "location_matched": loc_matched
                })

        return discovered

    def run_scout_cycle(
        self,
        profile: CandidateMasterProfile,
        target_boards: Optional[List[str]] = None,
        location_filters: Optional[List[str]] = None,
        live_submit: bool = False,
        max_applications_per_cycle: int = 5
    ) -> List[Dict]:
        """Executes full discovery and location-filtered application cycle."""
        self.console.print(f"\n[bold green]=== Starting Location-Aware Auto-Scout Cycle ===[/bold green]")
        locs = location_filters or getattr(profile, "preferred_locations", [])
        self.console.print(f"Target Locations: [cyan]{', '.join(locs) if locs else 'Any'}[/cyan]")
        self.console.print(f"Mode: {'[bold red]LIVE SUBMISSION[/bold red]' if live_submit else '[bold cyan]SAFE DRY-RUN STAGING[/bold cyan]'}\n")

        candidates = self.search_and_filter_jobs(
            profile=profile,
            target_boards=target_boards,
            location_filters=locs
        )

        unapplied = [c for c in candidates if not c.get("already_applied")]
        self.console.print(f"[bold cyan]Discovered {len(unapplied)} unapplied openings matching your location and roles.[/bold cyan]\n")

        processed = 0
        cycle_results = []

        for item in unapplied:
            if processed >= max_applications_per_cycle:
                self.console.print(f"[yellow]Reached cycle limit ({max_applications_per_cycle} applications).[/yellow]")
                break

            self.console.print(f"\n[bold]Evaluating & Applying:[/bold] {item['title']} at {item['board'].upper()} ({item['location']})")
            try:
                res = self.pipeline.execute_for_url(
                    job_url=item["url"],
                    profile=profile,
                    force_manual=False,
                    dry_run=not live_submit
                )
                if res.get("status") == "SUCCESS":
                    processed += 1
                    cycle_results.append(res)
            except Exception as e:
                self.console.print(f"[red]Error on {item['url']}: {e}[/red]")

            time.sleep(1.5)

        self.console.print(f"\n[bold green]Cycle complete. Applied/staged: {processed}[/bold green]")
        return cycle_results
