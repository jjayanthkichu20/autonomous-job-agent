"""Recruiter Email Classifier: Parses incoming emails to categorize intent and extract scheduling links."""

import re
from typing import List, Optional
from autonomous_job_agent.core.models import (
    RecruiterEmailAnalysis,
    RecruiterIntent
)


class RecruiterEmailClassifier:
    """Classifies inbound recruiter communications and identifies required actions."""

    REJECTION_PHRASES = [
        "not moving forward", "other candidates", "unfortunately",
        "decided to pursue", "impressive background, however", "not a match at this time"
    ]
    
    INTERVIEW_PHRASES = [
        "schedule a call", "invitation to interview", "phone screen",
        "chat about your background", "speak with the hiring manager",
        "next round", "availability for a quick call"
    ]

    ASSESSMENT_PHRASES = [
        "technical assessment", "coding challenge", "hackerrank", "codesignal", "take-home"
    ]

    OFFER_PHRASES = [
        "offer letter", "pleased to offer", "compensation package", "formal offer"
    ]

    ACKNOWLEDGEMENT_PHRASES = [
        "thank you for applying", "we have received your application", "application received"
    ]

    def analyze(self, sender: str, subject: str, body: str) -> RecruiterEmailAnalysis:
        lower_body = body.lower()
        lower_subject = subject.lower()
        combined = f"{lower_subject} {lower_body}"

        # 1. Intent Detection
        intent = RecruiterIntent.GENERAL_INQUIRY
        urgency = "MEDIUM"
        requires_human = False

        if any(p in combined for p in self.OFFER_PHRASES):
            intent = RecruiterIntent.OFFER
            urgency = "CRITICAL"
            requires_human = True
        elif any(p in combined for p in self.INTERVIEW_PHRASES):
            intent = RecruiterIntent.INTERVIEW_REQUEST
            urgency = "HIGH"
            requires_human = True
        elif any(p in combined for p in self.ASSESSMENT_PHRASES):
            intent = RecruiterIntent.TECHNICAL_ASSESSMENT
            urgency = "HIGH"
            requires_human = True
        elif any(p in combined for p in self.REJECTION_PHRASES):
            intent = RecruiterIntent.REJECTION
            urgency = "LOW"
            requires_human = False
        elif any(p in combined for p in self.ACKNOWLEDGEMENT_PHRASES):
            intent = RecruiterIntent.ACKNOWLEDGEMENT
            urgency = "LOW"
            requires_human = False

        # 2. Extract Scheduling Links (Calendly, Cal.com, etc.)
        link_pattern = r"https?://(?:www\.)?(?:calendly\.com|cal\.com|goodtime\.io|hubspot\.com/meetings)/[a-zA-Z0-9_\-\./]+"
        links = re.findall(link_pattern, body, re.IGNORECASE)
        booking_link = links[0] if links else None

        # 3. Extract Proposed Dates / Time Slots
        slot_pattern = r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?\s*\d{1,2}(?:st|nd|rd|th)?\s*(?:at|@)?\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|est|pst|cst|gmt|utc)"
        proposed_slots = re.findall(slot_pattern, lower_body, re.IGNORECASE)

        # 4. Extract Sender / Company Name
        company_name = None
        if "@" in sender:
            domain = sender.split("@")[-1].split(".")[0]
            if domain not in ["gmail", "yahoo", "outlook", "hotmail", "icloud"]:
                company_name = domain.capitalize()

        # 5. Summarize Action
        if intent == RecruiterIntent.INTERVIEW_REQUEST:
            action_summary = "Recruiter requested an interview. Slot confirmation needed."
        elif intent == RecruiterIntent.OFFER:
            action_summary = "Formal offer or compensation terms received! Immediate review required."
        elif intent == RecruiterIntent.REJECTION:
            action_summary = "Application concluded by employer. Status updated to rejected."
        elif intent == RecruiterIntent.ACKNOWLEDGEMENT:
            action_summary = "Application confirmed received. Follow-up queued for T+7 days."
        else:
            action_summary = "General recruiter communication parsed."

        return RecruiterEmailAnalysis(
            sender_email=sender,
            sender_name=sender.split("<")[0].strip() or "Recruiter",
            company_name=company_name,
            subject=subject,
            intent=intent,
            urgency_level=urgency,
            proposed_slots=proposed_slots[:3],
            booking_link=booking_link,
            requires_human_attention=requires_human,
            action_summary=action_summary
        )
