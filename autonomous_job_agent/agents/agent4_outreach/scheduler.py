"""Outreach Coordinator & Interview Scheduling Assistant."""

from typing import List, Optional
from autonomous_job_agent.core.models import (
    CandidateMasterProfile,
    JobPosting,
    RecruiterEmailAnalysis
)


class OutreachCoordinator:
    """Manages interview scheduling replies, follow-up sequences, and recruiter outreach."""

    @staticmethod
    def generate_interview_confirmation_reply(
        profile: CandidateMasterProfile,
        analysis: RecruiterEmailAnalysis,
        selected_slot: Optional[str] = None
    ) -> str:
        """Drafts a response confirming an interview slot."""
        greeting = f"Hi {analysis.sender_name}," if analysis.sender_name else "Hello,"
        
        if selected_slot:
            slot_text = f"I would be glad to meet on {selected_slot}."
        elif analysis.booking_link:
            slot_text = f"I have booked a slot via your scheduling link ({analysis.booking_link})."
        else:
            slot_text = "I am available this week on Tuesday and Thursday afternoons (EST) for a call."

        reply = (
            f"{greeting}\n\n"
            f"Thank you for reaching out. {slot_text} "
            f"Looking forward to speaking and learning more about the team's upcoming priorities.\n\n"
            f"Best regards,\n"
            f"{profile.first_name} {profile.last_name}\n"
            f"{profile.phone} | {profile.email}"
        )
        return reply

    @staticmethod
    def generate_followup_message(
        profile: CandidateMasterProfile,
        job: JobPosting,
        cadence_stage: str = "T+7"
    ) -> str:
        """Generates polite, professional status follow-up emails."""
        if cadence_stage == "T+7":
            subject = f"Following up on application: {job.job_title} - {profile.first_name} {profile.last_name}"
            body = (
                f"Dear {job.company_name} Hiring Team,\n\n"
                f"I hope you are having a productive week. I wanted to follow up on my recent application for the "
                f"{job.job_title} position submitted last week.\n\n"
                f"I remain very enthusiastic about the role and confident that my background in "
                f"{', '.join(job.required_skills[:3]) or 'software engineering'} would bring immediate value to your projects. "
                f"Please let me know if there are any additional materials or details I can provide.\n\n"
                f"Thank you for your time and consideration.\n\n"
                f"Sincerely,\n"
                f"{profile.first_name} {profile.last_name}\n"
                f"{profile.email} | {profile.phone}"
            )
        else:  # T+14
            subject = f"Status check: {job.job_title} - {profile.first_name} {profile.last_name}"
            body = (
                f"Dear {job.company_name} Hiring Team,\n\n"
                f"I am writing a brief note to check on the status of the {job.job_title} opening. "
                f"I understand your schedule is busy, and I appreciate the team's effort in reviewing candidates.\n\n"
                f"If the position has moved forward with other applicants, I completely understand and hope to stay in touch "
                f"for future opportunities.\n\n"
                f"Best regards,\n"
                f"{profile.first_name} {profile.last_name}"
            )

        return f"Subject: {subject}\n\n{body}"
