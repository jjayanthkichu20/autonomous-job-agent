"""Job Scraper Engine: extracts, cleans, and normalizes job descriptions from ATS portals and web pages."""

import re
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

from autonomous_job_agent.core.config import config
from autonomous_job_agent.core.dedup import SimHash, normalize_job_url
from autonomous_job_agent.core.models import JobPosting, RemotePolicy, JobStatus


class JobScraperEngine:
    """Robust scraper supporting direct ATS APIs and dynamic HTML career pages."""

    COMMON_TECH_SKILLS = [
        # Engineering & Tech
        "python", "go", "golang", "java", "rust", "c++", "typescript", "javascript",
        "kubernetes", "docker", "aws", "gcp", "azure", "terraform", "grpc", "graphql",
        "postgresql", "postgres", "redis", "kafka", "elasticsearch", "mongodb",
        "react", "next.js", "vue", "django", "fastapi", "flask", "pytorch", "tensorflow",
        "ci/cd", "microservices", "distributed systems", "ebpf", "linux", "git",
        # HR, People Operations & Talent Acquisition
        "recruitment", "talent acquisition", "onboarding", "induction", "hrms", "hris",
        "payroll", "statutory compliance", "pf", "esi", "labour law", "employee relations",
        "employee lifecycle", "candidate screening", "interview coordination",
        "attendance", "leave management", "hr operations", "people operations", "hr generalist",
        "mis", "advanced excel", "excel", "hr analytics", "documentation",
        # Manufacturing & Precision Operations
        "cnc", "vmc", "machining", "quality inspection", "5s", "lean"
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.crawler_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.simhash = SimHash()

    def _check_verified_index(self, canonical_url: str, fuzzy: bool = False) -> Optional[JobPosting]:
        """Check if job exists in local storage/verified_job_index.json for offline/resilient execution."""
        from pathlib import Path
        import json
        idx_file = Path(__file__).resolve().parents[3] / "storage" / "verified_job_index.json"
        if not idx_file.exists():
            return None
        try:
            with open(idx_file, "r", encoding="utf-8") as f:
                jobs = json.load(f)
            target = None
            clean_url = canonical_url.rstrip("/").lower()
            for j in jobs:
                j_url = j.get("url", "").rstrip("/").lower()
                if j_url == clean_url:
                    target = j
                    break
                if fuzzy and (j_url.split("/")[-1] in clean_url or clean_url.split("/")[-1] in j_url):
                    target = j
                    break
            if target:
                remote_pol = RemotePolicy.REMOTE_WORLDWIDE if target.get("is_remote") else RemotePolicy.ONSITE
                sim_val = self.simhash.compute(target.get("raw_description", ""))
                return JobPosting(
                    canonical_url=target.get("url", canonical_url),
                    source_platform="verified_index",
                    company_name=target.get("board", "Target Company"),
                    job_title=target.get("title", "HR Opening"),
                    location=target.get("location", "Bangalore, India"),
                    remote_policy=remote_pol,
                    raw_description=target.get("raw_description", ""),
                    cleaned_description=target.get("raw_description", ""),
                    raw_html=f"<html><body><h1>{target.get('title')}</h1><h2>{target.get('board')}</h2><div class='location'>{target.get('location')}</div><div class='content'>{target.get('raw_description')}</div></body></html>",
                    required_skills=target.get("skills", []),
                    simhash_fingerprint=sim_val,
                    status=JobStatus.DISCOVERED
                )
        except Exception:
            pass
        return None

    def fetch_job(self, raw_url: str) -> JobPosting:
        """Fetch and normalize job posting from URL."""
        canonical_url = normalize_job_url(raw_url)
        parsed = urlparse(canonical_url)
        netloc = parsed.netloc.lower()

        # Check local verified index first if applicable
        indexed_job = self._check_verified_index(canonical_url)
        if indexed_job:
            return indexed_job

        time.sleep(config.request_delay_seconds)

        try:
            if "boards.greenhouse.io" in netloc or "job-boards.greenhouse.io" in netloc:
                return self._parse_greenhouse(canonical_url)
            elif "jobs.lever.co" in netloc:
                return self._parse_lever(canonical_url)
            else:
                return self._parse_generic_html(canonical_url)
        except requests.exceptions.HTTPError as e:
            fallback = self._check_verified_index(canonical_url, fuzzy=True)
            if fallback:
                return fallback
            raise ValueError(f"Target career page returned HTTP {e.response.status_code} ({e.response.reason}). Please ensure the job URL is active and not expired.") from e
        except requests.exceptions.RequestException as e:
            fallback = self._check_verified_index(canonical_url, fuzzy=True)
            if fallback:
                return fallback
            raise ValueError(f"Network error connecting to {netloc}: {str(e)}") from e

    def _parse_greenhouse(self, url: str) -> JobPosting:
        """Extract job data from Greenhouse job posting."""
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title_elem = soup.find("h1", class_="app-title") or soup.find("h1")
        title = title_elem.get_text(strip=True) if title_elem else "Software Engineer"

        company_elem = soup.find("span", class_="company-name") or soup.find("div", class_="company")
        company = company_elem.get_text(strip=True) if company_elem else "Target Company"

        location_elem = soup.find("div", class_="location") or soup.find("span", class_="location")
        location = location_elem.get_text(strip=True) if location_elem else "Remote"

        content_div = soup.find("div", id="content") or soup.find("div", class_="body") or soup
        raw_text = content_div.get_text(separator="\n", strip=True)

        return self._build_job_posting(
            url=url,
            platform="greenhouse",
            company=company,
            title=title,
            location=location,
            raw_text=raw_text,
            raw_html=resp.text
        )

    def _parse_lever(self, url: str) -> JobPosting:
        """Extract job data from Lever job posting."""
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title_elem = soup.find("h2") or soup.find("h1")
        title = title_elem.get_text(strip=True) if title_elem else "Software Engineer"

        company = "Target Company"
        title_tag = soup.find("title")
        if title_tag and "-" in title_tag.text:
            company = title_tag.text.split("-")[-1].strip()

        location_elem = soup.find("span", class_="sort-by-time") or soup.find("div", class_="location")
        location = location_elem.get_text(strip=True) if location_elem else "Remote"

        content_div = soup.find("div", class_="content") or soup
        raw_text = content_div.get_text(separator="\n", strip=True)

        return self._build_job_posting(
            url=url,
            platform="lever",
            company=company,
            title=title,
            location=location,
            raw_text=raw_text,
            raw_html=resp.text
        )

    def _parse_generic_html(self, url: str) -> JobPosting:
        """Extract job data from generic HTML web page."""
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Strip scripts and styles
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        title_elem = soup.find("h1")
        title = title_elem.get_text(strip=True) if title_elem else "Senior Engineer"

        parsed = urlparse(url)
        company = parsed.netloc.split(".")[0].capitalize()

        raw_text = soup.get_text(separator="\n", strip=True)
        return self._build_job_posting(
            url=url,
            platform="generic_web",
            company=company,
            title=title,
            location="Remote",
            raw_text=raw_text,
            raw_html=resp.text
        )

    def _build_job_posting(
        self, url: str, platform: str, company: str, title: str, location: str, raw_text: str, raw_html: Optional[str] = None
    ) -> JobPosting:
        # Clean text
        cleaned_text = re.sub(r"\n{3,}", "\n\n", raw_text).strip()
        simhash_val = self.simhash.compute(cleaned_text)

        # Detect remote policy
        lower_text = cleaned_text.lower()
        if "remote worldwide" in lower_text or "anywhere" in lower_text:
            remote_policy = RemotePolicy.REMOTE_WORLDWIDE
        elif "remote" in lower_text or "remote" in location.lower():
            remote_policy = RemotePolicy.REMOTE_COUNTRY
        elif "hybrid" in lower_text or "hybrid" in location.lower():
            remote_policy = RemotePolicy.HYBRID
        else:
            remote_policy = RemotePolicy.ONSITE

        # Extract salary range if present
        salary_match = re.search(r"\$(\d{2,3}),?(\d{3})\s*(?:-|to)\s*\$(\d{2,3}),?(\d{3})", cleaned_text)
        min_salary, max_salary = None, None
        if salary_match:
            min_salary = float(f"{salary_match.group(1)}{salary_match.group(2)}")
            max_salary = float(f"{salary_match.group(3)}{salary_match.group(4)}")

        # Extract required skills
        detected_skills = []
        for skill in self.COMMON_TECH_SKILLS:
            # Word boundary search
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, lower_text):
                detected_skills.append(skill)

        return JobPosting(
            canonical_url=url,
            source_platform=platform,
            company_name=company,
            job_title=title,
            location=location,
            remote_policy=remote_policy,
            raw_description=raw_text,
            cleaned_description=cleaned_text,
            raw_html=raw_html,
            min_salary_usd=min_salary,
            max_salary_usd=max_salary,
            required_skills=list(set(detected_skills)),
            simhash_fingerprint=simhash_val,
            status=JobStatus.DISCOVERED
        )
