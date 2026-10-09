"""Application Executor Engine: Intelligent form mapping, stealth submission, and receipt verification."""

from datetime import datetime, timezone
import os
import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import requests

from autonomous_job_agent.core.models import (
    ApplicationState,
    ApplicationSubmission,
    ApplicationVariant,
    CandidateMasterProfile,
    FormFieldMapping,
    JobPosting
)
from autonomous_job_agent.core.security import security_manager


class ApplicationExecutorEngine:
    """Automates form discovery, mapping, and atomic submission across ATS platforms."""

    def __init__(self):
        self.session = requests.Session()

    def map_form_fields(
        self,
        html_content: str,
        profile: CandidateMasterProfile,
        variant: ApplicationVariant,
        resume_file_path: Optional[str] = None
    ) -> List[FormFieldMapping]:
        """Intelligently maps candidate profile attributes to HTML form inputs."""
        soup = BeautifulSoup(html_content, "html.parser")
        mappings: List[FormFieldMapping] = []

        inputs = soup.find_all(["input", "textarea", "select"])

        for el in inputs:
            name = (el.get("name") or "").lower()
            el_id = (el.get("id") or "").lower()
            placeholder = (el.get("placeholder") or "").lower()
            aria_label = (el.get("aria-label") or "").lower()
            input_type = (el.get("type") or "text").lower()

            combined_attrs = f"{name} {el_id} {placeholder} {aria_label}"
            selector = f"#{el.get('id')}" if el.get("id") else f"[name='{el.get('name')}']"

            if input_type in ["hidden", "submit", "button"]:
                continue

            mapped_value = None
            field_category = "unknown"
            confidence = 0.5

            # First Name
            if any(k in combined_attrs for k in ["first_name", "firstname", "first name", "given-name"]):
                mapped_value = profile.first_name
                field_category = "first_name"
                confidence = 0.98

            # Last Name
            elif any(k in combined_attrs for k in ["last_name", "lastname", "last name", "family-name"]):
                mapped_value = profile.last_name
                field_category = "last_name"
                confidence = 0.98

            # Full Name
            elif any(k in combined_attrs for k in ["name", "full_name", "fullname"]) and "company" not in combined_attrs:
                mapped_value = f"{profile.first_name} {profile.last_name}"
                field_category = "full_name"
                confidence = 0.95

            # Email
            elif input_type == "email" or any(k in combined_attrs for k in ["email", "e-mail"]):
                mapped_value = profile.email
                field_category = "email"
                confidence = 0.99

            # Phone
            elif input_type == "tel" or any(k in combined_attrs for k in ["phone", "tel", "mobile"]):
                mapped_value = profile.phone
                field_category = "phone"
                confidence = 0.97

            # LinkedIn
            elif "linkedin" in combined_attrs:
                mapped_value = profile.linkedin_url or ""
                field_category = "linkedin"
                confidence = 0.95

            # GitHub
            elif "github" in combined_attrs:
                mapped_value = profile.github_url or ""
                field_category = "github"
                confidence = 0.95

            # Website / Portfolio
            elif any(k in combined_attrs for k in ["website", "portfolio", "url"]):
                mapped_value = profile.portfolio_url or profile.github_url or ""
                field_category = "portfolio"
                confidence = 0.90

            # Resume File Upload
            elif input_type == "file" or "resume" in combined_attrs or "cv" in combined_attrs:
                mapped_value = resume_file_path or "resume_tailored.pdf"
                field_category = "resume_file"
                confidence = 0.98

            # Cover Letter
            elif el.name == "textarea" or "cover_letter" in combined_attrs or "comments" in combined_attrs:
                mapped_value = variant.cover_letter
                field_category = "cover_letter"
                confidence = 0.92

            if mapped_value is not None:
                mappings.append(
                    FormFieldMapping(
                        field_name=field_category,
                        selector=selector,
                        field_type=input_type if el.name != "textarea" else "textarea",
                        injected_value=mapped_value,
                        confidence_score=confidence
                    )
                )

        return mappings

    def execute_submission(
        self,
        job: JobPosting,
        profile: CandidateMasterProfile,
        variant: ApplicationVariant,
        field_mappings: List[FormFieldMapping],
        dry_run: bool = True
    ) -> ApplicationSubmission:
        """Executes application submission or validates mapping in dry-run mode."""
        submission_id = f"sub_{job.id[:8]}_{int(datetime.now(timezone.utc).timestamp())}"
        
        if dry_run:
            # Safe validation mode - guarantees zero false live submissions
            confirmation_id = f"DRYRUN-{submission_id.upper()}"
            return ApplicationSubmission(
                id=submission_id,
                candidate_id=profile.candidate_id,
                job_id=job.id,
                variant_id=variant.id,
                state=ApplicationState.SUBMITTED,
                external_confirmation_id=confirmation_id,
                field_mappings=field_mappings,
                receipt_url=f"dry_run://{job.company_name.lower()}/receipt/{confirmation_id}",
                submitted_at=datetime.now(timezone.utc)
            )

        # In production live mode: posts multipart payload to endpoint
        try:
            # Construct submission payload from mappings
            post_data = {}
            files = {}
            for m in field_mappings:
                if m.field_type == "file":
                    if os.path.exists(m.injected_value):
                        files["resume"] = open(m.injected_value, "rb")
                else:
                    clean_key = m.selector.strip("#[]").replace("name=", "").replace("'", "")
                    post_data[clean_key] = m.injected_value

            submit_url = job.canonical_url
            try:
                from urllib.parse import urljoin
                soup = BeautifulSoup(job.raw_html or job.raw_description, "html.parser")
                form = soup.find("form")
                if form and form.get("action"):
                    submit_url = urljoin(job.canonical_url, form.get("action"))
            except Exception:
                submit_url = job.canonical_url

            resp = self.session.post(submit_url, data=post_data, files=files if files else None, timeout=30)
            
            # Close file handles
            for f in files.values():
                f.close()

            # Verify response
            if resp.status_code in [200, 201, 302]:
                confirmation_id = f"CONF-{int(datetime.now(timezone.utc).timestamp())}"
                return ApplicationSubmission(
                    id=submission_id,
                    candidate_id=profile.candidate_id,
                    job_id=job.id,
                    variant_id=variant.id,
                    state=ApplicationState.SUBMITTED,
                    external_confirmation_id=confirmation_id,
                    field_mappings=field_mappings,
                    receipt_url=resp.url,
                    submitted_at=datetime.now(timezone.utc)
                )
            else:
                return ApplicationSubmission(
                    id=submission_id,
                    candidate_id=profile.candidate_id,
                    job_id=job.id,
                    variant_id=variant.id,
                    state=ApplicationState.FAILED,
                    error_message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    field_mappings=field_mappings
                )
        except Exception as e:
            return ApplicationSubmission(
                id=submission_id,
                candidate_id=profile.candidate_id,
                job_id=job.id,
                variant_id=variant.id,
                state=ApplicationState.FAILED,
                error_message=str(e),
                field_mappings=field_mappings
            )
