"""Comprehensive test suite for the Autonomous Multi-Agent Suite."""

import json
from pathlib import Path
import pytest

from autonomous_job_agent.core.dedup import SimHash, normalize_job_url
from autonomous_job_agent.core.security import security_manager
from autonomous_job_agent.core.models import (
    CandidateMasterProfile,
    JobPosting,
    RemotePolicy,
    RecruiterIntent
)
from autonomous_job_agent.agents.agent1_scraper.relevance_scorer import RelevanceScorer
from autonomous_job_agent.agents.agent2_customizer.tailor_engine import CVTailorEngine
from autonomous_job_agent.agents.agent3_executor.executor_engine import ApplicationExecutorEngine
from autonomous_job_agent.agents.agent4_outreach.email_classifier import RecruiterEmailClassifier
from autonomous_job_agent.mock_ats.server import MockATSServer
from autonomous_job_agent.orchestration.pipeline import AutonomousJobApplicationPipeline


@pytest.fixture
def sample_profile():
    profile_path = Path(__file__).resolve().parent.parent / "sample_candidate_profile.json"
    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return CandidateMasterProfile(**data)


def test_simhash_deduplication():
    simhash = SimHash()
    text_a = "We are seeking a Senior Distributed Systems Engineer to design cloud architecture with Kubernetes and Go."
    text_b = "We are seeking a Senior Distributed Systems Engineer to design cloud architecture with Kubernetes, Go, and Docker."
    text_c = "Experienced marketing specialist needed for social media branding campaigns and paid search management."

    hash_a = simhash.compute(text_a)
    hash_b = simhash.compute(text_b)
    hash_c = simhash.compute(text_c)

    # Near duplicates should have small Hamming distance
    assert simhash.hamming_distance(hash_a, hash_b) <= 8
    assert simhash.is_duplicate(text_a, text_b, max_distance=8) is True

    # Completely different text should have high Hamming distance
    assert simhash.hamming_distance(hash_a, hash_c) >= 18


def test_url_canonicalization():
    raw_url = "https://boards.greenhouse.io/company/jobs/12345?gh_src=linkedin&utm_source=feed#apply"
    expected = "https://boards.greenhouse.io/company/jobs/12345"
    assert normalize_job_url(raw_url) == expected


def test_envelope_encryption_roundtrip():
    dek = security_manager.generate_candidate_dek()
    encrypted_dek = security_manager.encrypt_candidate_dek(dek)
    decrypted_dek = security_manager.decrypt_candidate_dek(encrypted_dek)
    assert dek == decrypted_dek

    sensitive_payload = {"ssn": "000-12-3456", "phone": "+1-555-019-4829"}
    ciphertext = security_manager.encrypt_payload(sensitive_payload, dek)
    decrypted_payload = security_manager.decrypt_payload(ciphertext, dek)
    assert decrypted_payload == sensitive_payload


def test_relevance_hard_filter_salary(sample_profile):
    scorer = RelevanceScorer()
    
    # Job salary below candidate minimum ($160k)
    low_paying_job = JobPosting(
        canonical_url="https://test.com/job/1",
        source_platform="test",
        company_name="LowPay Corp",
        job_title="Senior Engineer",
        location="Remote",
        raw_description="Python Go engineer",
        cleaned_description="Python Go engineer",
        max_salary_usd=120000.0,
        required_skills=["python", "go"]
    )
    score = scorer.evaluate(low_paying_job, sample_profile)
    assert score.hard_filter_passed is False
    assert score.overall_score <= 0.35
    assert "below candidate floor" in score.rationale


def test_agent2_grounded_tailoring(sample_profile):
    tailor = CVTailorEngine()
    scorer = RelevanceScorer()
    job = JobPosting(
        canonical_url="https://test.com/job/2",
        source_platform="test",
        company_name="HighScale Systems",
        job_title="Senior Infrastructure Engineer",
        location="Remote",
        raw_description="Looking for Go, eBPF, and Kubernetes engineers.",
        cleaned_description="Looking for Go, eBPF, and Kubernetes engineers.",
        required_skills=["go", "ebpf", "kubernetes"],
        max_salary_usd=200000.0
    )
    relevance = scorer.evaluate(job, sample_profile)
    variant = tailor.tailor(sample_profile, job, relevance)

    assert len(variant.bullet_diffs) > 0
    # Every bullet must have an anchored fact ID from the profile
    for diff in variant.bullet_diffs:
        assert len(diff.anchored_fact_ids) > 0
        assert diff.anchored_fact_ids[0].startswith("ach_")
    assert "HighScale Systems" in variant.cover_letter


def test_agent4_email_classification():
    classifier = RecruiterEmailClassifier()

    # Case 1: Interview request with Calendly link
    body_interview = "Hi Alex, we'd like to schedule an interview with you. Please book a time here: https://calendly.com/tech/interview"
    analysis_interview = classifier.analyze("recruiter@tech.com", "Invitation to Interview", body_interview)
    assert analysis_interview.intent == RecruiterIntent.INTERVIEW_REQUEST
    assert analysis_interview.requires_human_attention is True
    assert "calendly.com" in analysis_interview.booking_link

    # Case 2: Rejection
    body_rejection = "Thank you for your time. Unfortunately, we have decided to pursue other candidates."
    analysis_rejection = classifier.analyze("no-reply@company.com", "Application Status", body_rejection)
    assert analysis_rejection.intent == RecruiterIntent.REJECTION
    assert analysis_rejection.requires_human_attention is False


def test_end_to_end_mock_pipeline_run(sample_profile):
    server = MockATSServer(port=8769)
    server.start()
    try:
        pipeline = AutonomousJobApplicationPipeline()
        mock_url = "http://127.0.0.1:8769/greenhouse/job/101"
        
        result = pipeline.execute_for_url(
            job_url=mock_url,
            profile=sample_profile,
            force_manual=False,
            dry_run=True
        )

        assert result["status"] == "SUCCESS"
        assert result["relevance"].overall_score > 0.70
        assert result["submission"].external_confirmation_id.startswith("DRYRUN-")
        assert Path(result["artifacts"]["markdown_path"]).exists()
    finally:
        server.stop()


def test_ledger_classification_and_updates():
    from autonomous_job_agent.core.ledger import ApplicationLedger
    import tempfile

    test_ledger = ApplicationLedger()
    
    # 1. Test classifications
    live_app = {"status": "SUBMITTED", "confirmation_id": "CONF-1791517525"}
    cls_live = test_ledger.classify_entry(live_app)
    assert cls_live["is_live"] is True
    assert cls_live["tier"] == "LIVE"

    staged_app = {"status": "SUBMITTED", "confirmation_id": "DRYRUN-SUB_12345_6789"}
    cls_staged = test_ledger.classify_entry(staged_app)
    assert cls_staged["is_staged"] is True
    assert cls_staged["tier"] == "DRY_RUN"

    interview_app = {"status": "INTERVIEW_SCHEDULED", "confirmation_id": "CONF-999"}
    cls_interview = test_ledger.classify_entry(interview_app)
    assert cls_interview["is_interview"] is True
    assert cls_interview["tier"] == "INTERVIEW"

    # 2. Test status & interview update
    test_url = "https://test-company.local/jobs/hr-specialist"
    test_ledger.record_entry(
        job_id="test_job_001",
        company_name="Test Corp",
        job_title="HR Specialist",
        job_url=test_url,
        relevance_score=0.95,
        status="SUBMITTED",
        confirmation_id="CONF-TEST-123"
    )

    updated = test_ledger.update_application(
        job_url_or_id=test_url,
        new_status="INTERVIEW_SCHEDULED",
        notes="Hiring manager screening scheduled",
        interview_date="2026-10-20",
        interview_time="14:30",
        interview_round="Round 1 Screening",
        meeting_link="https://meet.google.com/test-abc-xyz"
    )
    assert updated is not None
    assert updated["status"] == "INTERVIEW_SCHEDULED"
    assert updated["interview_date"] == "2026-10-20"
    assert updated["interview_round"] == "Round 1 Screening"

    # 3. Test follow-up logging
    followed_up = test_ledger.record_followup(test_url, cadence="T+7", notes="Polite check-in sent")
    assert followed_up is not None
    assert followed_up["status"] == "FOLLOW_UP_SENT"
    assert len(followed_up["followup_history"]) >= 1


def test_custom_jd_service_tailoring_and_apply(sample_profile):
    from autonomous_job_agent.agents.agent2_customizer.custom_jd_service import custom_jd_service

    profile_path = Path(__file__).resolve().parent.parent / "my_profile.json"
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            test_profile = CandidateMasterProfile(**json.load(f))
    else:
        test_profile = sample_profile

    jd_text = """
    We are seeking an HR Operations Executive to join our team in Bangalore / Remote.
    Responsibilities:
    - Oversee employee onboarding, documentation, and induction programs.
    - Manage HRIS data entry, employee lifecycle records, and personnel files.
    - Ensure statutory compliance including PF, ESI, and Labour Law adherence.
    - Support talent acquisition with interview scheduling and candidate engagement.
    Qualifications:
    - 2+ years experience in HR operations or talent acquisition.
    - Proficiency in HRMS, Microsoft Excel, and labour compliance.
    """

    result = custom_jd_service.tailor_from_jd_text(
        profile=test_profile,
        job_title="HR Operations Executive",
        company_name="Swiggy Technologies",
        jd_text=jd_text,
        location="Bangalore, Karnataka, India / Remote"
    )

    assert result["match_score"] >= 80
    assert len(result["matched_skills"]) >= 2
    assert any(s.lower() in ("hr operations", "onboarding", "hris") for s in result["matched_skills"])
    assert "Swiggy Technologies" in result["cover_letter"]
    assert len(result["bullet_diffs"]) >= 1
    assert Path(result["artifacts_dir"]).exists()
    assert (Path(result["artifacts_dir"]) / "tailored_resume.pdf").exists()

    # Test applying
    applied = custom_jd_service.apply_for_custom_jd(
        profile=test_profile,
        draft_id=result["draft_id"],
        dry_run=True
    )
    assert applied["status"] == "success"
    assert applied["delivery_status"] == "STAGED"
    assert applied["confirmation_id"].startswith("DRYRUN-")

