"""Relevance Scorer: Evaluates job postings against candidate profile with hard filters and multi-factor scoring."""

import re
from typing import List, Tuple
from autonomous_job_agent.core.models import (
    CandidateMasterProfile,
    JobPosting,
    RelevanceScore,
    RemotePolicy
)
from autonomous_job_agent.core.role_matcher import is_target_role_match


class RelevanceScorer:
    """Evaluates suitability of discovered job postings for a specific candidate."""

    SENIORITY_LEVELS = ["intern", "junior", "mid", "senior", "staff", "principal", "lead", "director"]

    def evaluate(self, job: JobPosting, profile: CandidateMasterProfile) -> RelevanceScore:
        # 1. Hard Filter Checks
        hard_filter_passed = True
        filter_failures = []

        # Role and Title match check
        role_matched, role_reason = is_target_role_match(job.job_title, profile.target_roles)
        if not role_matched:
            hard_filter_passed = False
            filter_failures.append(f"Job title does not match candidate target roles: {role_reason}")

        # Salary floor check
        if profile.min_desired_salary_usd and job.max_salary_usd:
            if job.max_salary_usd < profile.min_desired_salary_usd:
                hard_filter_passed = False
                filter_failures.append(
                    f"Job max salary (${job.max_salary_usd:,.0f}) is below candidate floor (${profile.min_desired_salary_usd:,.0f})"
                )

        # 2. Skill Overlap Calculation
        candidate_skills = set()
        raw_skills_pool = list(profile.verified_skills)
        for exp in profile.experiences:
            for ach in exp.achievements:
                raw_skills_pool.extend(ach.skills)

        for s in raw_skills_pool:
            s_lower = s.lower().strip()
            candidate_skills.add(s_lower)
            for sub in re.split(r"[/&,()]", s_lower):
                clean_sub = sub.strip()
                if len(clean_sub) > 2:
                    candidate_skills.add(clean_sub)

        job_skills = {s.lower() for s in job.required_skills}
        matched_skills = sorted(list(candidate_skills.intersection(job_skills)))
        missing_skills = sorted(list(job_skills.difference(candidate_skills)))

        if job_skills:
            skill_overlap_ratio = len(matched_skills) / len(job_skills)
        else:
            skill_overlap_ratio = 0.7  # Default assumption if job listed no explicit tech tags

        # 3. Title / Target Role Alignment
        title_overlap_score = 0.0
        job_title_lower = job.job_title.lower()
        for target in profile.target_roles:
            target_words = set(target.lower().split())
            job_title_words = set(job_title_lower.split())
            intersection = target_words.intersection(job_title_words)
            if intersection:
                ratio = len(intersection) / len(target_words)
                if ratio > title_overlap_score:
                    title_overlap_score = ratio

        # 4. Location Compatibility Evaluation
        target_locs = []
        if getattr(profile, "preferred_locations", None):
            target_locs = [l.lower().strip() for l in profile.preferred_locations if l]
        elif profile.location:
            target_locs = [l.lower().strip() for l in re.split(r"[,/|()]", profile.location) if len(l.strip()) > 2]

        job_loc_lower = (job.location or "").lower()
        is_remote_job = (
            job.remote_policy in (RemotePolicy.REMOTE_WORLDWIDE, RemotePolicy.REMOTE_COUNTRY)
            or any(kw in job_loc_lower for kw in ["remote", "anywhere", "worldwide", "distributed", "virtual", "work from home"])
        )

        location_matched = False
        if is_remote_job:
            location_matched = True
            location_score = 1.0
            loc_label = "Remote / Anywhere"
        elif any(loc in job_loc_lower for loc in target_locs if loc):
            location_matched = True
            location_score = 1.0
            loc_label = f"Matched Target Location: {job.location}"
        elif any(c in target_locs for c in ["india", "bangalore", "kerala"]) and ("india" in job_loc_lower or any(c in job_loc_lower for c in ["bengaluru", "bangalore", "kerala", "mumbai", "hyderabad", "chennai", "pune", "delhi", "gurgaon"])):
            location_matched = True
            location_score = 0.85
            loc_label = f"Regional Match (India): {job.location}"
        else:
            location_score = 0.20
            loc_label = f"Location Mismatch: {job.location} vs {target_locs[:3]}"

        # 5. Seniority Evaluation
        candidate_years = len(profile.experiences) * 2.0  # Approximation
        seniority_alignment = "Aligned"
        if "staff" in job_title_lower or "principal" in job_title_lower:
            seniority_alignment = "Staff/Principal Level"
        elif "senior" in job_title_lower or "lead" in job_title_lower:
            seniority_alignment = "Senior Level"
        elif "junior" in job_title_lower or "intern" in job_title_lower:
            seniority_alignment = "Entry Level"

        # 6. Composite Score Computation
        # Weighting: 40% Skill Match, 30% Title Match, 20% Location Match, 10% Baseline
        raw_score = (0.40 * skill_overlap_ratio) + (0.30 * title_overlap_score) + (0.20 * location_score) + 0.10

        if not hard_filter_passed:
            composite_score = min(0.35, raw_score * 0.5)
            rationale = "Failed hard filters: " + "; ".join(filter_failures)
        else:
            composite_score = min(1.0, max(0.0, raw_score))
            rationale = (
                f"Matched {len(matched_skills)}/{len(job_skills)} skills. "
                f"Title match: {title_overlap_score:.0%}. Location: {loc_label} ({location_score:.0%})."
            )

        return RelevanceScore(
            job_id=job.id,
            candidate_id=profile.candidate_id,
            overall_score=round(composite_score, 3),
            hard_filter_passed=hard_filter_passed,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            seniority_alignment=seniority_alignment,
            rationale=rationale
        )
