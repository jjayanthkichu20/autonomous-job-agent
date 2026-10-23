"""Role Matcher: Validates job titles against candidate target roles, career tracks, and filters out non-matching titles."""

import re
from typing import Dict, List, Optional, Tuple

NEGATIVE_TITLE_TERMS = [
    "engineer",
    "engineering",
    "developer",
    "software",
    "architect",
    "threat",
    "security",
    "cybersecurity",
    "fraud",
    "product design",
    "creative & communications",
    "internal communications",
    "sales executive",
    "data scientist",
    "frontend",
    "backend",
    "full stack",
    "fullstack",
    "devops",
    "sre",
    "qa engineer",
    "test engineer",
    "designer",
    "scientist",
    "threat hunting",
    "ads fraud",
    "risk assessment manager",
    "hardware",
    "network admin",
    "devops engineer",
    "cloud architect"
]

POSITIVE_ROLE_CATEGORIES: Dict[str, List[str]] = {
    "HR Executive": [
        r"\bhr executive\b",
        r"\bhuman resources executive\b",
        r"\bhr officer\b",
        r"\bhr associate\b",
        r"\bhr generalist\b",
        r"\bassociate hr\b",
        r"\bjunior hr\b",
        r"\bsenior hr executive\b",
        r"\bassistant hr executive\b",
        r"\bhr specialist\b",
        r"\bhr compliance\b",
        r"\bhr coordinator\b",
        r"\bregional hr\b"
    ],
    "HR Operations": [
        r"\bhr operations\b",
        r"\bpeople operations\b",
        r"\bpeople ops\b",
        r"\bpeople partner operations\b",
        r"\bpeople experience\b",
        r"\bhr shared services\b",
        r"\bemployee lifecycle\b",
        r"\bpeople support\b",
        r"\bonboarding\b",
        r"\bpayroll\b",
        r"\bpeople & culture operations\b",
        r"\bhrms\b",
        r"\bpersonnel\b"
    ],
    "Talent Acquisition": [
        r"\btalent acquisition\b",
        r"\brecruit",
        r"\btalent sourcing\b",
        r"\btalent operations\b",
        r"\btalent specialist\b",
        r"\btalent fulfillment\b",
        r"\btalent partner\b",
        r"\btalent strategist\b",
        r"\btalent coordinator\b",
        r"\btalent associate\b",
        r"\brecruiting coordinator\b"
    ],
    "People Operations": [
        r"\bpeople operations\b",
        r"\bpeople ops\b",
        r"\bpeople experience\b",
        r"\bpeople generalist\b",
        r"\bpeople partner\b",
        r"\bpeople support\b",
        r"\bpeople & culture\b"
    ]
}

ALL_HR_PATTERNS: List[str] = [
    r"\bhr\b",
    r"\bhuman resources\b",
    r"\btalent\b",
    r"\brecruit",
    r"\bpeople ops\b",
    r"\bpeople operations\b",
    r"\bpeople partner\b",
    r"\bpeople experience\b",
    r"\bpeople & culture\b",
    r"\bpeople generalist\b",
    r"\bpeople support\b",
    r"\bonboarding\b",
    r"\bpayroll\b",
    r"\bhrms\b",
    r"\bpersonnel\b"
]


def is_target_role_match(
    job_title: str,
    target_roles: Optional[List[str]] = None,
    selected_category: str = "ALL"
) -> Tuple[bool, str]:
    """
    Validates whether a job title matches candidate target roles and excludes non-matching domains.
    Returns (True, reason) if it matches, (False, reason) if it fails.
    """
    if not job_title or not job_title.strip():
        return False, "Empty job title"

    t = job_title.lower().strip()

    # Determine candidate track
    is_hr_candidate = True
    if target_roles:
        is_hr_candidate = any(
            any(k in r.lower() for k in ["hr", "people", "talent", "recruit", "onboarding"])
            for r in target_roles
        )

    if is_hr_candidate:
        # 1. Negative title filter: strictly discard engineering/threat/security/software roles for HR candidates
        for neg in NEGATIVE_TITLE_TERMS:
            if neg in t:
                return False, f"Negative keyword '{neg}' detected in job title for HR track"

        # 2. Specific role category filter (e.g. from UI filter button)
        cat = (selected_category or "ALL").strip()
        if cat != "ALL" and cat in POSITIVE_ROLE_CATEGORIES:
            for pat in POSITIVE_ROLE_CATEGORIES[cat]:
                if re.search(pat, t):
                    return True, f"Matched role category '{cat}'"
            return False, f"Title does not match requested category '{cat}'"

        # 3. Overall umbrella check for HR / Talent / People Ops
        for pat in ALL_HR_PATTERNS:
            if re.search(pat, t):
                return True, f"Matched HR pattern '{pat}'"
        return False, "Title does not match HR / Talent Acquisition / People Operations target roles"

    # Non-HR track (e.g. Engineering candidate): check target roles match
    if target_roles:
        for r in target_roles:
            target_words = {w for w in r.lower().split() if len(w) > 2 and w not in ["senior", "junior", "lead", "staff", "principal"]}
            title_words = {w for w in t.split() if len(w) > 2}
            if target_words and target_words.issubset(title_words):
                return True, f"Matched target role '{r}'"
            if target_words.intersection(title_words):
                return True, f"Matched target role words for '{r}'"
        return False, "Title does not match candidate target roles"

    return True, "No target role restrictions applied"
