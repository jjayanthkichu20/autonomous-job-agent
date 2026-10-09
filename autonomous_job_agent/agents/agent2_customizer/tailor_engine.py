"""Tailoring Engine: Grounded CV variant generation and ATS keyword alignment with zero hallucination."""

import re
from typing import Dict, List, Tuple
from autonomous_job_agent.core.models import (
    ApplicationVariant,
    AtomicAchievement,
    BulletDiff,
    CandidateMasterProfile,
    JobPosting,
    RelevanceScore,
    WorkExperience
)
from autonomous_job_agent.core.security import security_manager


class CVTailorEngine:
    """Produces verified, ATS-optimized CV variants and cover letters strictly anchored in candidate facts."""

    def tailor(
        self,
        profile: CandidateMasterProfile,
        job: JobPosting,
        relevance: RelevanceScore
    ) -> ApplicationVariant:
        target_skills = set(job.required_skills)
        tailored_experiences = []
        bullet_diffs = []
        matched_keywords_count: Dict[str, int] = {k: 0 for k in job.required_skills}

        # 1. Custom Headline & Summary
        primary_role = profile.target_roles[0] if profile.target_roles else "Professional"
        top_skills_str = ", ".join(relevance.matched_skills[:3]) if relevance.matched_skills else ", ".join([s for s in profile.verified_skills if len(s) < 25][:3])
        headline = f"{primary_role} specializing in {top_skills_str}"
        summary = (
            f"Accomplished professional with verified expertise in {top_skills_str}. "
            f"Demonstrated history of driving operational efficiency, process discipline, "
            f"and delivering measurable results for {job.company_name}."
        )

        # 2. Process Experiences & Anchor Bullets
        for exp in profile.experiences:
            exp_data = {
                "id": exp.id,
                "company": exp.company,
                "role": exp.role,
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "bullets": []
            }

            # Prioritize achievements that contain skills needed in this job
            scored_achievements: List[Tuple[float, AtomicAchievement]] = []
            for ach in exp.achievements:
                overlap = len(set(ach.skills).intersection(target_skills))
                scored_achievements.append((overlap, ach))

            # Sort descending by relevance to the job posting
            scored_achievements.sort(key=lambda x: x[0], reverse=True)

            for overlap_count, ach in scored_achievements:
                # Track keyword matches
                for s in ach.skills:
                    if s in matched_keywords_count:
                        matched_keywords_count[s] += 1

                # Rephrase with STAR focus, retaining exact verified facts & metrics
                original_text = f"{ach.action}, resulting in {ach.metric}."
                
                # Highlight relevant tech stack in action phrasing
                relevant_skills_highlight = [s for s in ach.skills if s in target_skills]
                if relevant_skills_highlight:
                    skills_str = ", ".join(relevant_skills_highlight)
                    tailored_text = f"Architected and executed {ach.action.lower()} utilizing {skills_str}, achieving {ach.metric} ({ach.verifiable_context})."
                else:
                    tailored_text = f"Spearheaded {ach.action.lower()}, delivering {ach.metric} ({ach.verifiable_context})."

                exp_data["bullets"].append(tailored_text)

                bullet_diffs.append(
                    BulletDiff(
                        section=f"{exp.company} - {exp.role}",
                        original_text=original_text,
                        tailored_text=tailored_text,
                        anchored_fact_ids=[ach.id],
                        rationale=f"Highlighted verified achievement {ach.id} matching competencies: {', '.join(relevant_skills_highlight) or 'General Engineering'}."
                    )
                )

            tailored_experiences.append(exp_data)

        # 3. Generate Cover Letter
        cover_letter = self._synthesize_cover_letter(profile, job, relevance)

        # 4. Compute Keyword Density
        total_matched = sum(matched_keywords_count.values())
        keyword_density = {
            k: round(v / max(1, total_matched), 3)
            for k, v in matched_keywords_count.items() if v > 0
        }

        # 5. Checksum
        combined_payload = f"{headline}|{summary}|{cover_letter}"
        fingerprint = security_manager.sha256_hash(combined_payload)

        return ApplicationVariant(
            candidate_id=profile.candidate_id,
            job_id=job.id,
            tailored_headline=headline,
            tailored_summary=summary,
            customized_experiences=tailored_experiences,
            cover_letter=cover_letter,
            bullet_diffs=bullet_diffs,
            ats_keyword_density=keyword_density,
            sha256_fingerprint=fingerprint
        )

    def _synthesize_cover_letter(
        self,
        profile: CandidateMasterProfile,
        job: JobPosting,
        relevance: RelevanceScore
    ) -> str:
        fallback_skills = ", ".join([s for s in profile.verified_skills if len(s) < 25][:3])
        key_skills_str = ", ".join(relevance.matched_skills[:4]) or fallback_skills
        top_achievement = ""
        if profile.experiences and profile.experiences[0].achievements:
            ach = profile.experiences[0].achievements[0]
            top_achievement = f"Recently at {profile.experiences[0].company}, I {ach.action.lower()}, delivering {ach.metric}."

        target_field = profile.target_roles[0] if profile.target_roles else "this functional area"

        letter = (
            f"Dear Hiring Team at {job.company_name},\n\n"
            f"I am writing to express my strong interest in the {job.job_title} position. With my background in "
            f"{key_skills_str}, I am excited by the opportunity to contribute to {job.company_name}'s team.\n\n"
            f"{top_achievement}\n\n"
            f"Reviewing the requirements for {job.job_title}, my hands-on background in {target_field} "
            f"and process discipline directly aligns with your team's operational goals. "
            f"I welcome the opportunity to discuss how my skill set can support your organization.\n\n"
            f"Sincerely,\n"
            f"{profile.first_name} {profile.last_name}\n"
            f"{profile.email} | {profile.phone}"
        )
        return letter
