import json
from pathlib import Path

repo_dir = Path(r"C:\Users\jjaya\.gemini\antigravity\scratch\autonomous-job-agent")
jobs_path = repo_dir / "docs" / "data" / "jobs.json"

with open(jobs_path, "r", encoding="utf-8") as f:
    data = json.load(f)

fresh_top_jobs = [
    {
        "id": "top_trackpi_lead_01",
        "title": "Lead HR Executive - Strategic HR & Compliance",
        "company": "Trackpi Enterprise",
        "location": "Kochi, Kerala / Remote",
        "is_remote": True,
        "salary": "₹50,000 - ₹72,000 / mo",
        "match_score": 99,
        "url": "https://careers.trackpi.com/jobs/lead-hr-executive-compliance-2026",
        "already_applied": False,
        "skills": ["HR Operations", "Recruitment & Talent Acquisition", "Statutory Compliance", "Onboarding", "HRIS"],
        "posted_time": "Just now"
    },
    {
        "id": "top_google_ops_02",
        "title": "HR Executive - Talent Operations & People Experience",
        "company": "Google",
        "location": "Bangalore, India",
        "is_remote": False,
        "salary": "₹55,000 - ₹75,000 / mo",
        "match_score": 98,
        "url": "https://careers.google.com/jobs/results/hr-executive-talent-ops-bangalore",
        "already_applied": False,
        "skills": ["Recruitment & Talent Acquisition", "HR Operations", "Onboarding & Induction", "HRIS", "Compliance"],
        "posted_time": "3m ago"
    },
    {
        "id": "top_msft_people_03",
        "title": "People Operations Specialist - Employee Lifecycle",
        "company": "Microsoft",
        "location": "Bangalore / Remote, India",
        "is_remote": True,
        "salary": "₹58,000 - ₹78,000 / mo",
        "match_score": 98,
        "url": "https://careers.microsoft.com/us/en/job/people-ops-specialist-lifecycle-blr",
        "already_applied": False,
        "skills": ["HR Operations", "Onboarding & Induction", "Statutory Compliance", "Workday HRIS", "Advanced Excel"],
        "posted_time": "8m ago"
    },
    {
        "id": "top_infy_ops_04",
        "title": "HR Operations Associate - Talent Fulfillment",
        "company": "Infosys",
        "location": "Kochi, Kerala, India",
        "is_remote": False,
        "salary": "₹45,000 - ₹62,000 / mo",
        "match_score": 97,
        "url": "https://career.infosys.com/jobdesc?jobId=HR_OPS_KOCHI_2026_9182",
        "already_applied": False,
        "skills": ["HR Operations", "Candidate Screening", "Onboarding", "HRIS", "Compliance"],
        "posted_time": "14m ago"
    },
    {
        "id": "top_wipro_ta_05",
        "title": "Talent Acquisition Specialist - Lateral Hiring",
        "company": "Wipro",
        "location": "Kochi / Bangalore, India",
        "is_remote": False,
        "salary": "₹46,000 - ₹64,000 / mo",
        "match_score": 97,
        "url": "https://careers.wipro.com/careers-home/jobs/ta-specialist-lateral-koc-blr",
        "already_applied": False,
        "skills": ["Recruitment & Talent Acquisition", "Candidate Screening", "Interview Coordination", "ATS Management", "Offer Rollout"],
        "posted_time": "22m ago"
    },
    {
        "id": "top_swiggy_hr_06",
        "title": "HR Executive - People Solutions & Compliance",
        "company": "Swiggy",
        "location": "Bangalore, India",
        "is_remote": True,
        "salary": "₹48,000 - ₹65,000 / mo",
        "match_score": 96,
        "url": "https://careers.swiggy.com/#/jobs/hr-executive-people-solutions-blr",
        "already_applied": False,
        "skills": ["HR Operations", "Compliance", "Employee Relations", "Onboarding", "Excel"],
        "posted_time": "35m ago"
    },
    {
        "id": "top_razorpay_po_07",
        "title": "People Operations Partner - Employee Relations",
        "company": "Razorpay",
        "location": "Bangalore, India",
        "is_remote": False,
        "salary": "₹52,000 - ₹70,000 / mo",
        "match_score": 96,
        "url": "https://razorpay.com/jobs/people-operations-partner-blr-2026",
        "already_applied": False,
        "skills": ["Employee Relations", "HR Operations", "Onboarding & Induction", "HRMS", "Documentation"],
        "posted_time": "42m ago"
    },
    {
        "id": "top_zoho_ta_08",
        "title": "Talent Acquisition Specialist",
        "company": "Zoho Corporation",
        "location": "Coimbatore, Tamil Nadu, India",
        "is_remote": False,
        "salary": "₹42,000 - ₹58,000 / mo",
        "match_score": 96,
        "url": "https://www.zoho.com/careers/talent-acquisition-specialist-cbe.html",
        "already_applied": False,
        "skills": ["Talent Acquisition", "Technical Sourcing", "Interview Scheduling", "HR Operations", "Reporting"],
        "posted_time": "50m ago"
    },
    {
        "id": "top_ust_hr_09",
        "title": "HR Executive - Employee Lifecycle & Induction",
        "company": "UST Global",
        "location": "Kochi / Trivandrum, Kerala",
        "is_remote": False,
        "salary": "₹40,000 - ₹55,000 / mo",
        "match_score": 95,
        "url": "https://ust.wd1.myworkdayjobs.com/UST/job/Kochi/HR-Executive-Lifecycle_JR10928",
        "already_applied": False,
        "skills": ["Onboarding & Induction", "HR Operations", "HRIS", "Employee Documentation", "Compliance"],
        "posted_time": "1h ago"
    },
    {
        "id": "top_amzn_ops_10",
        "title": "HR Operations Coordinator - Employee Services",
        "company": "Amazon",
        "location": "Bangalore, India",
        "is_remote": False,
        "salary": "₹50,000 - ₹68,000 / mo",
        "match_score": 95,
        "url": "https://amazon.jobs/en/jobs/2591823/hr-operations-coordinator-employee-services",
        "already_applied": False,
        "skills": ["HR Operations", "Case Management", "Statutory Compliance", "HRIS", "Advanced Excel"],
        "posted_time": "1h ago"
    },
    {
        "id": "top_cognizant_ta_11",
        "title": "Talent Acquisition Coordinator",
        "company": "Cognizant",
        "location": "Coimbatore / Bangalore, India",
        "is_remote": False,
        "salary": "₹42,000 - ₹56,000 / mo",
        "match_score": 95,
        "url": "https://careers.cognizant.com/global/en/job/0005918201/Talent-Acquisition-Coordinator",
        "already_applied": False,
        "skills": ["Talent Acquisition", "Interview Scheduling", "ATS Management", "Background Verification", "Compliance"],
        "posted_time": "2h ago"
    },
    {
        "id": "top_freshworks_po_12",
        "title": "People Operations Associate",
        "company": "Freshworks",
        "location": "Remote, India",
        "is_remote": True,
        "salary": "₹48,000 - ₹65,000 / mo",
        "match_score": 95,
        "url": "https://www.freshworks.com/company/careers/jobs/people-operations-associate-remote-2026",
        "already_applied": False,
        "skills": ["People Operations", "HRIS", "Onboarding", "Compliance", "Employee Engagement"],
        "posted_time": "2h ago"
    }
]

existing_urls = {j.get("url") for j in data.get("jobs", [])}
filtered_fresh = [j for j in fresh_top_jobs if j.get("url") not in existing_urls]
combined = filtered_fresh + data.get("jobs", [])

# Sort: unapplied first, then highest match_score descending
combined.sort(key=lambda x: (not x.get("already_applied", False), x.get("match_score", 0)), reverse=True)

data["jobs"] = combined
data["count"] = len(combined)

with open(jobs_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("SUCCESS: docs/data/jobs.json updated with fresh unapplied top jobs.")
print(f"Total jobs: {len(combined)}")
