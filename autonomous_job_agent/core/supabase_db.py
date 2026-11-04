"""Supabase Cloud Database Client & Synchronization Engine

Provides direct PostgREST REST integration with Supabase for:
- Candidate profiles
- Active job feed with real-time sync
- Application ledger records
- Drafts and interview coordination
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger("supabase_db")

REPO_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = REPO_DIR / "storage" / "supabase_config.json"
DOCS_DATA_DIR = REPO_DIR / "docs" / "data"


class SupabaseDB:
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.url = url or os.environ.get("SUPABASE_URL")
        self.key = key or os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

        # Load persisted config from file if not in environment
        if not (self.url and self.key) and CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.url = self.url or cfg.get("url")
                    self.key = self.key or cfg.get("key")
            except Exception as e:
                logger.warning(f"Failed to read supabase_config.json: {e}")

        if self.url:
            self.url = self.url.rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.url and self.key)

    def save_config(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"url": self.url, "key": self.key}, f, indent=2)
        logger.info("Saved Supabase configuration to storage/supabase_config.json")

    def _headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def test_connection(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {"connected": False, "error": "Supabase URL and API Key are not configured."}
        try:
            # Query profiles table or root endpoint
            endpoint = f"{self.url}/rest/v1/profiles?select=id&limit=1"
            resp = requests.get(endpoint, headers=self._headers(), timeout=6)
            if resp.status_code in [200, 206]:
                return {"connected": True, "message": "Successfully connected to Supabase database!"}
            elif resp.status_code == 404:
                return {
                    "connected": False,
                    "error": "Connected to Supabase, but tables are missing. Please run 'supabase_schema.sql' in your Supabase SQL Editor."
                }
            else:
                return {"connected": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    # ==========================================
    # JOBS OPERATIONS
    # ==========================================
    def get_jobs(self, limit: int = 150) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        try:
            # Order: unapplied first, highest match_score descending
            endpoint = f"{self.url}/rest/v1/jobs?select=*&order=already_applied.asc,match_score.desc&limit={limit}"
            resp = requests.get(endpoint, headers=self._headers(), timeout=8)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"Failed to fetch jobs from Supabase: {resp.status_code} {resp.text}")
            return []
        except Exception as e:
            logger.error(f"Error fetching jobs from Supabase: {e}")
            return []

    def upsert_jobs(self, jobs: List[Dict[str, Any]]) -> bool:
        if not self.is_configured() or not jobs:
            return False
        try:
            endpoint = f"{self.url}/rest/v1/jobs"
            # PostgREST merge duplicates on primary key
            headers = self._headers(prefer="resolution=merge-duplicates,return=representation")
            # Batch in chunks of 50
            for i in range(0, len(jobs), 50):
                chunk = jobs[i:i + 50]
                resp = requests.post(endpoint, headers=headers, json=chunk, timeout=12)
                if resp.status_code not in [200, 201]:
                    logger.warning(f"Batch upsert chunk failed: {resp.status_code} {resp.text}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error upserting jobs to Supabase: {e}")
            return False

    def mark_job_applied(self, job_url: str) -> bool:
        if not self.is_configured():
            return False
        try:
            endpoint = f"{self.url}/rest/v1/jobs?url=eq.{requests.utils.quote(job_url)}"
            resp = requests.patch(endpoint, headers=self._headers(), json={"already_applied": True}, timeout=6)
            return resp.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Error marking job applied in Supabase: {e}")
            return False

    # ==========================================
    # APPLICATION LEDGER OPERATIONS
    # ==========================================
    def get_applications(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        try:
            endpoint = f"{self.url}/rest/v1/applications?select=*&order=applied_at.desc&limit={limit}"
            resp = requests.get(endpoint, headers=self._headers(), timeout=8)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.error(f"Error fetching applications: {e}")
            return []

    def record_application(self, app_data: Dict[str, Any]) -> bool:
        if not self.is_configured():
            return False
        try:
            endpoint = f"{self.url}/rest/v1/applications"
            headers = self._headers(prefer="resolution=merge-duplicates,return=representation")
            resp = requests.post(endpoint, headers=headers, json=app_data, timeout=8)
            if resp.status_code in [200, 201]:
                # Also mark job as applied if url exists
                if app_data.get("job_url"):
                    self.mark_job_applied(app_data["job_url"])
                return True
            return False
        except Exception as e:
            logger.error(f"Error recording application in Supabase: {e}")
            return False

    # ==========================================
    # PROFILE OPERATIONS
    # ==========================================
    def get_profile(self, profile_id: str = "cand_jayanth") -> Optional[Dict[str, Any]]:
        if not self.is_configured():
            return None
        try:
            endpoint = f"{self.url}/rest/v1/profiles?id=eq.{profile_id}&select=*"
            resp = requests.get(endpoint, headers=self._headers(), timeout=6)
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    return rows[0].get("raw_profile") or rows[0]
            return None
        except Exception as e:
            logger.error(f"Error getting profile from Supabase: {e}")
            return None

    def upsert_profile(self, profile_data: Dict[str, Any]) -> bool:
        if not self.is_configured():
            return False
        try:
            profile_id = profile_data.get("candidate_id") or "cand_jayanth"
            payload = {
                "id": profile_id,
                "first_name": profile_data.get("first_name", "JAYANTH"),
                "last_name": profile_data.get("last_name", "J"),
                "email": profile_data.get("email"),
                "phone": profile_data.get("phone"),
                "linkedin_url": profile_data.get("linkedin_url"),
                "location": profile_data.get("location"),
                "preferred_locations": profile_data.get("preferred_locations", []),
                "target_roles": profile_data.get("target_roles", []),
                "verified_skills": profile_data.get("verified_skills", []),
                "min_desired_salary_usd": profile_data.get("min_desired_salary_usd", 0),
                "experiences": profile_data.get("experiences", []),
                "education": profile_data.get("education", []),
                "certifications": profile_data.get("certifications", []),
                "raw_profile": profile_data
            }
            endpoint = f"{self.url}/rest/v1/profiles"
            headers = self._headers(prefer="resolution=merge-duplicates,return=representation")
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=8)
            return resp.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Error saving profile to Supabase: {e}")
            return False

    # ==========================================
    # SYNC ALL LOCAL DATA TO SUPABASE
    # ==========================================
    def sync_all_local_data(self) -> Dict[str, Any]:
        """Pushes local JSON files (profile, jobs, ledger) into Supabase."""
        if not self.is_configured():
            return {"success": False, "error": "Supabase is not configured."}

        results = {"profile": False, "jobs_synced": 0, "applications_synced": 0}

        # 1. Sync Profile
        profile_file = DOCS_DATA_DIR / "profile.json"
        if profile_file.exists():
            try:
                with open(profile_file, "r", encoding="utf-8") as f:
                    p_data = json.load(f)
                results["profile"] = self.upsert_profile(p_data)
            except Exception as e:
                logger.warning(f"Profile sync error: {e}")

        # 2. Sync Jobs
        jobs_file = DOCS_DATA_DIR / "jobs.json"
        if jobs_file.exists():
            try:
                with open(jobs_file, "r", encoding="utf-8") as f:
                    j_data = json.load(f)
                jobs = j_data.get("jobs", [])
                if self.upsert_jobs(jobs):
                    results["jobs_synced"] = len(jobs)
            except Exception as e:
                logger.warning(f"Jobs sync error: {e}")

        # 3. Sync Applications Ledger
        ledger_file = DOCS_DATA_DIR / "ledger.json"
        if ledger_file.exists():
            try:
                with open(ledger_file, "r", encoding="utf-8") as f:
                    l_data = json.load(f)
                apps = l_data.get("applications", [])
                headers = self._headers(prefer="resolution=merge-duplicates")
                endpoint = f"{self.url}/rest/v1/applications"
                for i in range(0, len(apps), 50):
                    chunk = apps[i:i + 50]
                    resp = requests.post(endpoint, headers=headers, json=chunk, timeout=12)
                    if resp.status_code in [200, 201]:
                        results["applications_synced"] += len(chunk)
            except Exception as e:
                logger.warning(f"Ledger sync error: {e}")

        return {"success": True, "details": results}


# Global singleton instance
supabase_db = SupabaseDB()
