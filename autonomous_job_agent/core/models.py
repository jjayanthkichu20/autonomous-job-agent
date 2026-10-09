"""Data models and schemas for the Autonomous Multi-Agent Job Application Suite."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, HttpUrl


class RemotePolicy(str, Enum):
    ONSITE = "ONSITE"
    HYBRID = "HYBRID"
    REMOTE_COUNTRY = "REMOTE_COUNTRY"
    REMOTE_WORLDWIDE = "REMOTE_WORLDWIDE"


class JobStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    SCORED = "SCORED"
    ELIGIBLE = "ELIGIBLE"
    FILTERED_OUT = "FILTERED_OUT"
    ARCHIVED = "ARCHIVED"


class ApplicationState(str, Enum):
    QUEUED = "QUEUED"
    PENDING_HITL_APPROVAL = "PENDING_HITL_APPROVAL"
    APPROVED = "APPROVED"
    RUNNING = "RUNNING"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"
    REJECTED_BY_USER = "REJECTED_BY_USER"


class RecruiterIntent(str, Enum):
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"
    REJECTION = "REJECTION"
    INTERVIEW_REQUEST = "INTERVIEW_REQUEST"
    TECHNICAL_ASSESSMENT = "TECHNICAL_ASSESSMENT"
    OFFER = "OFFER"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"
    SPAM = "SPAM"


# 1. Candidate Master Truth Store Models
class AtomicAchievement(BaseModel):
    id: str = Field(..., description="Unique fact anchor identifier, e.g. ach_001")
    metric: str = Field(..., description="Quantified outcome, e.g. 42% latency reduction")
    action: str = Field(..., description="Technical implementation executed")
    skills: List[str] = Field(default_factory=list, description="Specific skills verified in this achievement")
    verifiable_context: str = Field(..., description="Surrounding context verifiable during reference checks")


class WorkExperience(BaseModel):
    id: str = Field(..., description="Unique experience ID, e.g. exp_001")
    company: str
    role: str
    location: Optional[str] = None
    start_date: str  # YYYY-MM
    end_date: Optional[str] = None  # None indicates Current
    achievements: List[AtomicAchievement] = Field(default_factory=list)


class EducationEntry(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    graduation_year: int


class CandidateMasterProfile(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid4()))
    first_name: str
    last_name: str
    email: str
    phone: str
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    location: str
    preferred_locations: List[str] = Field(default_factory=list)
    target_roles: List[str] = Field(default_factory=list)
    verified_skills: List[str] = Field(default_factory=list)
    min_desired_salary_usd: Optional[float] = None
    experiences: List[WorkExperience] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    version: int = 1


# 2. Job Posting & Scraper Models
class JobPosting(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    canonical_url: str
    source_platform: str  # e.g., 'greenhouse', 'lever', 'custom'
    company_name: str
    job_title: str
    normalized_title: Optional[str] = None
    location: str
    remote_policy: RemotePolicy = RemotePolicy.ONSITE
    raw_description: str
    cleaned_description: str
    raw_html: Optional[str] = None
    min_salary_usd: Optional[float] = None
    max_salary_usd: Optional[float] = None
    required_skills: List[str] = Field(default_factory=list)
    simhash_fingerprint: int = 0
    status: JobStatus = JobStatus.DISCOVERED
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 3. Relevance & Evaluation Models
class RelevanceScore(BaseModel):
    job_id: str
    candidate_id: str
    overall_score: float = Field(..., ge=0.0, le=1.0)
    bm25_score: float = 0.0
    vector_similarity: float = 0.0
    hard_filter_passed: bool = True
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    seniority_alignment: str = "Aligned"
    rationale: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 4. Tailoring & CV Variant Models
class BulletDiff(BaseModel):
    section: str
    original_text: str
    tailored_text: str
    anchored_fact_ids: List[str] = Field(..., description="Fact IDs from master profile justifying this line")
    rationale: str


class ApplicationVariant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    candidate_id: str
    job_id: str
    tailored_headline: str
    tailored_summary: str
    customized_experiences: List[Dict]  # Structured experience objects with anchored bullets
    cover_letter: str
    bullet_diffs: List[BulletDiff] = Field(default_factory=list)
    ats_keyword_density: Dict[str, float] = Field(default_factory=dict)
    sha256_fingerprint: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 5. Application Execution Models
class FormFieldMapping(BaseModel):
    field_name: str
    selector: str
    field_type: str  # text, email, file, select, radio, textarea
    injected_value: str
    confidence_score: float


class ApplicationSubmission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    candidate_id: str
    job_id: str
    variant_id: str
    state: ApplicationState = ApplicationState.QUEUED
    external_confirmation_id: Optional[str] = None
    receipt_url: Optional[str] = None
    preflight_screenshot_path: Optional[str] = None
    field_mappings: List[FormFieldMapping] = Field(default_factory=list)
    error_message: Optional[str] = None
    retry_count: int = 0
    submitted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# 6. Recruiter Outreach Models
class RecruiterEmailAnalysis(BaseModel):
    sender_email: str
    sender_name: str
    company_name: Optional[str] = None
    subject: str
    intent: RecruiterIntent
    urgency_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    proposed_slots: List[str] = Field(default_factory=list)
    booking_link: Optional[str] = None
    requires_human_attention: bool = False
    action_summary: str


class InterviewEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    application_id: str
    meeting_title: str
    meeting_link: Optional[str] = None
    slot_time: str
    is_confirmed: bool = False


# 7. Audit Logging
class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str
    agent_component: str
    action: str
    details: Dict
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
