"""Auto-Scout Engine: Resilient discovery across career boards, location-aware matching, and auto-apply."""

import concurrent.futures
from datetime import datetime, timezone
import json
from pathlib import Path
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
    "freshworks",
    "stripe",
    "cloudflare",
    "figma",
    "reddit",
    "gusto",
    "brex",
    "coinbase",
    "dropbox",
    "airbnb",
    "robinhood",
    "duolingo",
    "twilio",
    "elastic",
    "mongodb"
]


class AutoScoutEngine:
    """Discovers openings across company career boards, filters by location, and triggers the application pipeline."""

    def __init__(self):
        self.console = Console()
        self.pipeline = AutonomousJobApplicationPipeline()

    def discover_jobs_on_greenhouse(self, board_name: str) -> List[Dict]:
        """Queries public Greenhouse API for active postings with resilient fast timeout."""
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_name}/jobs"
        try:
            resp = requests.get(api_url, timeout=3.5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("jobs", [])
        except Exception as e:
            self.console.print(f"[dim red]Error querying board '{board_name}': {e}[/dim red]")
        return []

    def is_within_max_age(self, job_dict: Dict, max_age_hours: Optional[int]) -> bool:
        """Determines if a job posting was published or updated within max_age_hours."""
        if not max_age_hours:
            return True

        # Check posted_time string (e.g. '1h ago', '3h ago', '1d ago')
        pt = (job_dict.get("posted_time") or "").lower().strip()
        if pt:
            if any(term in pt for term in ["m ago", "min", "just now", "fresh"]):
                return True
            if "h ago" in pt or "hr" in pt:
                try:
                    num_match = re.search(r"(\d+)\s*(?:h|hr)", pt)
                    if num_match:
                        return int(num_match.group(1)) <= max_age_hours
                except Exception:
                    pass
            if any(old in pt for old in ["d ago", "day", "w ago", "week", "mo ago", "month", "yr", "year"]):
                return False

        # Check first_published or updated_at ISO timestamp
        pub_str = job_dict.get("first_published") or job_dict.get("updated_at")
        if pub_str:
            try:
                dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                age_hours = (now - dt).total_seconds() / 3600.0
                return age_hours <= max_age_hours
            except Exception:
                pass

        return True

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
            # Coimbatore Synonyms
            if clean_loc in ("coimbatore", "kovai", "tamil nadu", "tamilnadu") and any(c in j_loc for c in ["coimbatore", "kovai", "tamil nadu", "tamilnadu", "saravanampatti", "peelamedu", "tidel"]):
                return True
            # Bangalore Synonyms
            if clean_loc in ("bangalore", "bengaluru") and any(b in j_loc for b in ["bangalore", "bengaluru", "whitefield", "koramangala", "bellandur", "electronic city", "hsr"]):
                return True
            # Kerala Synonyms
            if clean_loc in ("kerala", "kottayam", "cochin", "kochi", "trivandrum", "thiruvananthapuram", "calicut", "kozhikode") and any(k in j_loc for k in ["kerala", "kottayam", "cochin", "kochi", "trivandrum", "thiruvananthapuram", "calicut", "kozhikode", "infopark", "smartcity", "technopark", "kakkanad"]):
                return True
            # Gulf / UAE Synonyms
            if clean_loc in ("uae", "dubai", "abu dhabi") and any(u in j_loc for u in ["uae", "dubai", "abu dhabi", "emirates"]):
                return True
            # India Wide
            if clean_loc == "india" and any(ind in j_loc for ind in ["india", "bangalore", "bengaluru", "mumbai", "delhi", "gurgaon", "noida", "hyderabad", "chennai", "pune", "kerala", "coimbatore"]):
                return True
        return False

    def search_and_filter_jobs(
        self,
        profile: CandidateMasterProfile,
        target_boards: Optional[List[str]] = None,
        location_filters: Optional[List[str]] = None,
        keyword_filter: Optional[str] = None,
        max_age_hours: Optional[int] = None
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
        def fetch_board(b_name):
            return b_name, self.discover_jobs_on_greenhouse(b_name)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            board_results = list(executor.map(fetch_board, boards))

        for board, raw_jobs in board_results:
            for j in raw_jobs:
                title = j.get("title", "")
                title_lower = title.lower()
                loc_name = j.get("location", {}).get("name", "Remote/Unspecified")
                job_url = j.get("absolute_url")

                # Freshness check
                if max_age_hours and not self.is_within_max_age(j, max_age_hours):
                    continue

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
                    "posted_time": j.get("posted_time", "Fresh (< 12h)"),
                    "first_published": j.get("first_published"),
                    "already_applied": already_applied,
                    "is_remote": any(r in loc_name.lower() for r in ["remote", "anywhere", "worldwide"]),
                    "location_matched": loc_matched
                })

        # Resilient merge: Always include verified job index openings if not already in discovered
        verified_file = Path(__file__).resolve().parents[2] / "storage" / "verified_job_index.json"
        if verified_file.exists():
            try:
                with open(verified_file, "r", encoding="utf-8") as f:
                    v_jobs = json.load(f)
                existing_urls = {d.get("url") for d in discovered}
                for vj in v_jobs:
                    job_url = vj.get("url")
                    if job_url in existing_urls:
                        continue

                    # Freshness check
                    if max_age_hours and not self.is_within_max_age(vj, max_age_hours):
                        continue

                    title = vj.get("title", "")
                    title_lower = title.lower()
                    loc_name = vj.get("location", "Remote")

                    # Keyword match
                    if is_hr_profile:
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
                        "board": vj.get("board", "Company"),
                        "title": title,
                        "location": loc_name,
                        "url": job_url,
                        "posted_time": vj.get("posted_time", "Fresh (< 12h)"),
                        "first_published": vj.get("first_published"),
                        "salary": vj.get("salary"),
                        "already_applied": already_applied,
                        "is_remote": vj.get("is_remote", False),
                        "location_matched": loc_matched
                    })
            except Exception as ex:
                self.console.print(f"[red]Error loading verified job index: {ex}[/red]")

        return discovered

    def run_scout_cycle(
        self,
        profile: CandidateMasterProfile,
        target_boards: Optional[List[str]] = None,
        location_filters: Optional[List[str]] = None,
        live_submit: bool = False,
        max_applications_per_cycle: int = 5,
        max_age_hours: Optional[int] = None
    ) -> List[Dict]:
        """Executes full discovery and location-filtered application cycle."""
        self.console.print(f"\n[bold green]=== Starting Location-Aware Auto-Scout Cycle ===[/bold green]")
        locs = location_filters or getattr(profile, "preferred_locations", [])
        self.console.print(f"Target Locations: [cyan]{', '.join(locs) if locs else 'Any'}[/cyan]")
        if max_age_hours:
            self.console.print(f"Freshness Filter: [cyan]Jobs posted in last {max_age_hours} hours[/cyan]")
        self.console.print(f"Mode: {'[bold red]LIVE SUBMISSION[/bold red]' if live_submit else '[bold cyan]SAFE DRY-RUN STAGING[/bold cyan]'}\n")

        candidates = self.search_and_filter_jobs(
            profile=profile,
            target_boards=target_boards,
            location_filters=locs,
            max_age_hours=max_age_hours
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
