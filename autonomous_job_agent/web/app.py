"""Production-grade Web Platform & REST API for Autonomous Job Application Suite."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from autonomous_job_agent.core.config import config
from autonomous_job_agent.core.ledger import ledger
from autonomous_job_agent.core.models import CandidateMasterProfile, JobPosting
from autonomous_job_agent.orchestration.pipeline import AutonomousJobApplicationPipeline
from autonomous_job_agent.mock_ats.server import MockATSServer
from autonomous_job_agent.agents.agent4_outreach.email_classifier import RecruiterEmailClassifier
from autonomous_job_agent.orchestration.auto_scout import AutoScoutEngine
from autonomous_job_agent.core.pdf_parser import extract_text_from_pdf, parse_resume_text
from autonomous_job_agent.core.pdf_generator import generate_candidate_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_platform")

app = FastAPI(
    title="Autonomous AI Job Application Platform",
    description="End-to-end recruitment automation, CV reconstruction, and recruiter interaction dashboard",
    version="2.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor_pool = ThreadPoolExecutor(max_workers=4)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def get_profile_path() -> Path:
    p1 = BASE_DIR / "my_profile.json"
    if p1.exists():
        return p1
    p2 = BASE_DIR / "sample_candidate_profile.json"
    if p2.exists():
        return p2
    return p1


def load_current_profile() -> CandidateMasterProfile:
    path = get_profile_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Candidate profile file not found.")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return CandidateMasterProfile(**data)


# Request & Response Schemas
class ApplyRequest(BaseModel):
    job_url: str = Field(..., description="Target job posting URL")
    dry_run: bool = Field(default=True, description="Dry-run safety assertion mode")
    force_manual: bool = Field(default=False, description="Require manual approval before submission")


class EmailClassifyRequest(BaseModel):
    subject: str = Field(..., description="Recruiter email subject")
    body: str = Field(..., description="Email body text")
    company_name: Optional[str] = "Company"


class AutoScoutRequest(BaseModel):
    boards: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    max_apps: int = Field(default=3, ge=1, le=10)
    live_submit: bool = False


class JobSearchRequest(BaseModel):
    keywords: Optional[str] = "HR"
    locations: List[str] = Field(default_factory=lambda: ["Bangalore", "Kerala", "UAE", "Remote", "India"])
    boards: Optional[List[str]] = None


class BatchApplyRequest(BaseModel):
    job_urls: List[str] = Field(..., description="List of target job URLs to apply to")
    dry_run: bool = True


# Endpoints
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "system": "Autonomous Multi-Agent Job Application Suite",
        "version": "2.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/profile")
def get_profile():
    profile = load_current_profile()
    return profile.model_dump()


@app.post("/api/profile")
def update_profile(profile_data: Dict[str, Any]):
    try:
        validated = CandidateMasterProfile(**profile_data)
        path = BASE_DIR / "my_profile.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(validated.model_dump(), f, indent=2)
        return {"status": "success", "message": "Candidate master profile updated successfully", "profile": validated.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")


@app.post("/api/profile/upload-pdf")
async def upload_pdf_resume(file: UploadFile = File(...)):
    """Upload a PDF CV, parse it into CandidateMasterProfile, and update active truth store."""
    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Only .pdf or .txt resume files are supported.")
    
    content = await file.read()
    if file.filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(content)
    else:
        text = content.decode("utf-8", errors="ignore")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract readable text from the uploaded file.")

    parsed_dict = parse_resume_text(text, filename=file.filename)
    validated = CandidateMasterProfile(**parsed_dict)
    
    path = BASE_DIR / "my_profile.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(validated.model_dump(), f, indent=2)

    return {
        "status": "success",
        "message": f"Resume '{file.filename}' parsed and saved as active profile!",
        "profile": validated.model_dump()
    }


@app.get("/api/profile/download-pdf")
def download_resume_pdf():
    profile = load_current_profile()
    pdf_bytes = generate_candidate_pdf(profile)
    filename = f"{profile.first_name}_{profile.last_name}_Resume.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/ledger")
def get_ledger():
    data = ledger._load_data()
    apps = data.get("applications", [])
    
    total = len(apps)
    submitted = sum(1 for a in apps if a.get("status") in ("SUBMITTED", "APPLIED"))
    dry_run = sum(1 for a in apps if "DRY_RUN" in str(a.get("status", "")).upper() or "ASSERTION" in str(a.get("confirmation_id", "")))
    avg_relevance = (sum(a.get("relevance_score", 0) for a in apps) / total) if total > 0 else 0.0

    return {
        "summary": {
            "total_tracked": total,
            "submitted": submitted,
            "dry_run_verified": dry_run,
            "average_match_score": round(avg_relevance * 100, 1),
        },
        "applications": list(reversed(apps))
    }


# Live Job Search and Auto-Apply by Location
@app.post("/api/jobs/search")
async def search_jobs(req: JobSearchRequest):
    """Searches live career boards with location filtering."""
    def _execute():
        profile = load_current_profile()
        engine = AutoScoutEngine()
        locs = req.locations if req.locations else getattr(profile, "preferred_locations", [])
        jobs = engine.search_and_filter_jobs(
            profile=profile,
            target_boards=req.boards,
            location_filters=locs,
            keyword_filter=req.keywords
        )
        return {"status": "success", "count": len(jobs), "jobs": jobs}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor_pool, _execute)


@app.post("/api/jobs/batch-apply")
async def batch_apply(req: BatchApplyRequest):
    """Executes the pipeline for a selected list of job URLs according to location."""
    def _execute():
        profile = load_current_profile()
        pipeline = AutonomousJobApplicationPipeline()
        results = []
        for url in req.job_urls:
            try:
                res = pipeline.execute_for_url(
                    job_url=url,
                    profile=profile,
                    force_manual=False,
                    dry_run=req.dry_run
                )
                results.append(res)
            except Exception as e:
                results.append({"url": url, "status": "FAILED", "error": str(e)})
            time.sleep(1.0)
        return {"status": "completed", "processed": len(results), "results": results}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor_pool, _execute)


@app.post("/api/pipeline/run-mock")
async def run_mock_simulation():
    def _execute():
        server = MockATSServer(port=8899)
        server.start()
        try:
            profile = load_current_profile()
            pipeline = AutonomousJobApplicationPipeline()
            target_url = "http://127.0.0.1:8899/greenhouse/job/gh-78901"
            res = pipeline.execute_for_url(target_url, profile, dry_run=False)
            return res
        finally:
            server.stop()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor_pool, _execute)
    return {"status": "success", "result": result}


@app.post("/api/pipeline/apply")
async def apply_to_job(req: ApplyRequest):
    def _execute():
        profile = load_current_profile()
        pipeline = AutonomousJobApplicationPipeline()
        return pipeline.execute_for_url(
            job_url=req.job_url,
            profile=profile,
            force_manual=req.force_manual,
            dry_run=req.dry_run
        )

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(executor_pool, _execute)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception("Error executing pipeline")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recruiter/classify")
def classify_recruiter_email(req: EmailClassifyRequest):
    classifier = RecruiterEmailClassifier()
    classification = classifier.classify(req.subject, req.body)
    
    profile = load_current_profile()
    candidate_name = f"{profile.first_name} {profile.last_name}"
    
    if classification.intent.value == "INTERVIEW_REQUEST":
        followup_draft = (
            f"Dear Recruiter,\n\n"
            f"Thank you for reaching out! I would be delighted to speak further regarding the opportunity at {req.company_name}.\n"
            f"I have reviewed the available slots and look forward to speaking soon.\n\n"
            f"Best regards,\n{candidate_name}"
        )
    elif classification.intent.value == "TECHNICAL_ASSESSMENT":
        followup_draft = (
            f"Dear Recruiter,\n\n"
            f"Thank you for sharing the assessment details for {req.company_name}. "
            f"I have received the instructions and will complete the evaluation well within the indicated window.\n\n"
            f"Best regards,\n{candidate_name}"
        )
    else:
        followup_draft = (
            f"Dear Recruiter,\n\n"
            f"Thank you for the update regarding my application at {req.company_name}.\n\n"
            f"Best regards,\n{candidate_name}"
        )

    return {
        "intent": classification.intent.value,
        "confidence": classification.confidence,
        "suggested_action": classification.suggested_action,
        "scheduling_link": classification.scheduling_link,
        "deadline_hours": classification.deadline_hours,
        "draft_response": followup_draft
    }


@app.get("/api/compliance/export")
def gdpr_export():
    profile = load_current_profile()
    ledger_data = ledger._load_data()
    return {
        "compliance_standard": "GDPR Article 20 (Right to Data Portability)",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "candidate_profile": profile.model_dump(),
        "application_records": ledger_data.get("applications", [])
    }


@app.delete("/api/compliance/purge")
def gdpr_purge():
    ledger._save_data({"applications": []})
    return {
        "compliance_standard": "GDPR Article 17 (Right to Erasure)",
        "purged_at": datetime.now(timezone.utc).isoformat(),
        "status": "All application histories and tracking telemetry successfully erased."
    }


# Standalone Interactive Web Console UI
@app.get("/", response_class=HTMLResponse)
def index_view():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Autonomous AI Job Application Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; background-color: #0b0f19; color: #f3f4f6; }
    .glass-card { background: rgba(17, 24, 39, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .badge-submitted { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-dryrun { background-color: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-location { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-remote { background-color: rgba(139, 92, 246, 0.15); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.3); }
  </style>
</head>
<body class="min-h-screen flex flex-col">

  <!-- Toast Container -->
  <div id="toast-container" class="fixed top-5 right-5 z-50 flex flex-col space-y-3 pointer-events-none"></div>

  <!-- Top Navigation -->
  <header class="glass-card sticky top-0 z-40 px-6 py-4 border-b border-gray-800 flex items-center justify-between">
    <div class="flex items-center space-x-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/30">
        <i class="fa-solid fa-briefcase text-lg"></i>
      </div>
      <div>
        <h1 class="text-lg font-bold text-white tracking-wide">Autonomous Job Platform</h1>
        <p class="text-xs text-gray-400">Multi-Agent AI Recruitment Engine • v2.2</p>
      </div>
    </div>
    
    <div class="flex items-center space-x-4">
      <div class="flex items-center space-x-2 text-xs bg-emerald-950/60 text-emerald-400 px-3 py-1.5 rounded-full border border-emerald-500/30">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span>Scheduled Automation: <strong>Daily 9:00 AM (Location Filter Active)</strong></span>
      </div>
      <button onclick="triggerMockRun()" id="btn-quick-sim" class="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-all flex items-center space-x-2 shadow-lg shadow-blue-600/30">
        <i class="fa-solid fa-play"></i>
        <span>Run E2E Simulation</span>
      </button>
    </div>
  </header>

  <!-- Main Content Container -->
  <div class="flex-1 flex max-w-7xl w-full mx-auto p-6 gap-6">
    <!-- Sidebar Navigation -->
    <aside class="w-64 space-y-2">
      <button onclick="switchTab('dashboard')" id="nav-dashboard" class="w-full text-left px-4 py-3 rounded-xl flex items-center space-x-3 text-sm font-medium transition-colors bg-blue-600/20 text-blue-400 border border-blue-500/30">
        <i class="fa-solid fa-chart-line w-5"></i>
        <span>Dashboard & Funnel</span>
      </button>
      <button onclick="switchTab('scout')" id="nav-scout" class="w-full text-left px-4 py-3 rounded-xl flex items-center space-x-3 text-sm font-medium transition-colors text-gray-400 hover:text-white hover:bg-gray-800/50">
        <i class="fa-solid fa-earth-americas w-5 text-amber-400"></i>
        <span>Live Search & Location</span>
      </button>
      <button onclick="switchTab('profile')" id="nav-profile" class="w-full text-left px-4 py-3 rounded-xl flex items-center space-x-3 text-sm font-medium transition-colors text-gray-400 hover:text-white hover:bg-gray-800/50">
        <i class="fa-solid fa-file-pdf w-5 text-red-400"></i>
        <span>Upload & Manage CV</span>
      </button>
      <button onclick="switchTab('apply')" id="nav-apply" class="w-full text-left px-4 py-3 rounded-xl flex items-center space-x-3 text-sm font-medium transition-colors text-gray-400 hover:text-white hover:bg-gray-800/50">
        <i class="fa-solid fa-robot w-5"></i>
        <span>Single URL Runner</span>
      </button>
      <button onclick="switchTab('tracker')" id="nav-tracker" class="w-full text-left px-4 py-3 rounded-xl flex items-center space-x-3 text-sm font-medium transition-colors text-gray-400 hover:text-white hover:bg-gray-800/50">
        <i class="fa-solid fa-list-check w-5"></i>
        <span>Application Tracker</span>
      </button>
      <button onclick="switchTab('recruiter')" id="nav-recruiter" class="w-full text-left px-4 py-3 rounded-xl flex items-center space-x-3 text-sm font-medium transition-colors text-gray-400 hover:text-white hover:bg-gray-800/50">
        <i class="fa-solid fa-comments w-5"></i>
        <span>Recruiter Hub</span>
      </button>
      <button onclick="switchTab('compliance')" id="nav-compliance" class="w-full text-left px-4 py-3 rounded-xl flex items-center space-x-3 text-sm font-medium transition-colors text-gray-400 hover:text-white hover:bg-gray-800/50">
        <i class="fa-solid fa-shield-halved w-5"></i>
        <span>Privacy & Compliance</span>
      </button>
    </aside>

    <!-- Content Workspace -->
    <main class="flex-1 space-y-6">
      
      <!-- TAB 1: DASHBOARD -->
      <section id="tab-dashboard" class="space-y-6">
        <div class="grid grid-cols-4 gap-4">
          <div class="glass-card p-5 rounded-2xl">
            <div class="flex items-center justify-between text-gray-400 text-xs">
              <span>Total Tracked</span>
              <i class="fa-solid fa-briefcase text-blue-400"></i>
            </div>
            <div id="stat-total" class="text-2xl font-bold text-white mt-2">0</div>
            <div class="text-[11px] text-gray-500 mt-1">Discovered openings</div>
          </div>
          <div class="glass-card p-5 rounded-2xl">
            <div class="flex items-center justify-between text-gray-400 text-xs">
              <span>Applications Submitted</span>
              <i class="fa-solid fa-check-circle text-emerald-400"></i>
            </div>
            <div id="stat-submitted" class="text-2xl font-bold text-emerald-400 mt-2">0</div>
            <div class="text-[11px] text-gray-500 mt-1">Atomic form completions</div>
          </div>
          <div class="glass-card p-5 rounded-2xl">
            <div class="flex items-center justify-between text-gray-400 text-xs">
              <span>Pre-Flight Verified</span>
              <i class="fa-solid fa-shield-check text-indigo-400"></i>
            </div>
            <div id="stat-dryrun" class="text-2xl font-bold text-indigo-400 mt-2">0</div>
            <div class="text-[11px] text-gray-500 mt-1">Dry-run assertion passes</div>
          </div>
          <div class="glass-card p-5 rounded-2xl">
            <div class="flex items-center justify-between text-gray-400 text-xs">
              <span>Average JD Fit</span>
              <i class="fa-solid fa-bullseye text-amber-400"></i>
            </div>
            <div id="stat-fit" class="text-2xl font-bold text-amber-400 mt-2">0%</div>
            <div class="text-[11px] text-gray-500 mt-1">Semantic match score</div>
          </div>
        </div>

        <!-- Location Preferences Banner -->
        <div class="glass-card p-5 rounded-2xl flex items-center justify-between border-amber-500/20 bg-amber-950/10">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center text-lg">
              <i class="fa-solid fa-location-dot"></i>
            </div>
            <div>
              <h3 class="text-xs font-bold text-white">Active Location Filter Priorities</h3>
              <p class="text-[11px] text-gray-400 mt-0.5">Scouting & applying to: <strong class="text-amber-300">Bangalore, Kerala (Kottayam/Kochi), UAE/Dubai, India, and Remote Worldwide</strong></p>
            </div>
          </div>
          <button onclick="switchTab('scout')" class="bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-lg shadow-amber-600/30">
            <i class="fa-solid fa-magnifying-glass mr-1"></i> Search Live Openings
          </button>
        </div>

        <div class="glass-card p-6 rounded-2xl">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-sm font-semibold text-white flex items-center space-x-2">
              <i class="fa-solid fa-clock-rotate-left text-gray-400"></i>
              <span>Recent Application Activity</span>
            </h2>
            <button onclick="loadDashboard()" class="text-xs text-blue-400 hover:text-blue-300">
              <i class="fa-solid fa-arrows-rotate"></i> Refresh
            </button>
          </div>
          <div id="recent-ledger-table" class="overflow-x-auto text-xs">
            <p class="text-gray-500 py-4 text-center">Loading activity data...</p>
          </div>
        </div>
      </section>

      <!-- TAB 2: LIVE JOB SEARCH & LOCATION SCOUT -->
      <section id="tab-scout" class="space-y-6 hidden">
        <div class="glass-card p-6 rounded-2xl space-y-4">
          <div>
            <h2 class="text-base font-bold text-white flex items-center space-x-2">
              <i class="fa-solid fa-earth-americas text-amber-400"></i>
              <span>Live Job Search & Location-Aware Auto-Apply</span>
            </h2>
            <p class="text-xs text-gray-400 mt-1">Queries active career boards (Greenhouse, Lever) in real time and filters strictly by your selected target locations.</p>
          </div>

          <!-- Filters Row -->
          <div class="grid grid-cols-2 gap-4 pt-2">
            <div>
              <label class="block text-xs font-semibold text-gray-300 mb-1">Keywords / Roles</label>
              <input id="scout-keyword" type="text" value="HR Operations" class="w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-2 text-xs text-white">
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-300 mb-1">Target Locations (comma-separated)</label>
              <input id="scout-locations" type="text" value="Bangalore, Kerala, Dubai, UAE, India, Remote" class="w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-2 text-xs text-white">
            </div>
          </div>

          <div class="flex items-center justify-between pt-2">
            <div class="flex items-center space-x-4 text-xs">
              <label class="flex items-center space-x-2 cursor-pointer">
                <input id="scout-dry-run" type="checkbox" checked class="w-4 h-4 rounded bg-gray-900 border-gray-700 text-blue-600">
                <span class="text-gray-300 font-medium">Safe Dry-Run Assertion Mode</span>
              </label>
            </div>
            <div class="flex items-center space-x-3">
              <button onclick="executeLiveJobSearch()" id="btn-search-jobs" class="bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-amber-600/30">
                <i class="fa-solid fa-magnifying-glass mr-1.5"></i> Search Live Openings
              </button>
              <button onclick="autoApplySelected()" id="btn-batch-apply" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-emerald-600/30 hidden">
                <i class="fa-solid fa-paper-plane mr-1.5"></i> Auto-Apply to Selected (<span id="selected-count">0</span>)
              </button>
            </div>
          </div>
        </div>

        <!-- Discovered Jobs Table -->
        <div class="glass-card p-6 rounded-2xl">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-xs font-bold text-white flex items-center space-x-2">
              <i class="fa-solid fa-list-check text-blue-400"></i>
              <span>Discovered Live Postings (<span id="scout-results-count">0</span> matching location)</span>
            </h3>
            <button onclick="selectAllScoutJobs()" id="btn-select-all" class="text-xs text-blue-400 hover:underline hidden">Select All</button>
          </div>
          <div id="scout-results-table" class="overflow-x-auto text-xs">
            <p class="text-gray-500 py-6 text-center">Click 'Search Live Openings' above to discover postings matching your location preferences.</p>
          </div>
        </div>
      </section>

      <!-- TAB 3: UPLOAD & MANAGE CV -->
      <section id="tab-profile" class="space-y-6 hidden">
        <div class="glass-card p-6 rounded-2xl">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h2 class="text-base font-bold text-white flex items-center space-x-2">
                <i class="fa-solid fa-file-pdf text-red-400"></i>
                <span>Upload Candidate CV / Resume</span>
              </h2>
              <p class="text-xs text-gray-400">Upload your PDF resume. Our NLP parser automatically extracts your contact details, core skills, experience, and achievements into the master truth store.</p>
            </div>
            <a href="/api/profile/download-pdf" target="_blank" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-600/30 flex items-center space-x-2">
              <i class="fa-solid fa-download"></i>
              <span>Download CV as PDF</span>
            </a>
          </div>

          <div id="drop-zone" class="border-2 border-dashed border-gray-700 hover:border-blue-500 transition-colors rounded-2xl p-8 text-center cursor-pointer bg-gray-900/40">
            <input type="file" id="cv-file-input" accept=".pdf,.txt" class="hidden" onchange="handleFileUpload(event)">
            <div class="w-14 h-14 mx-auto rounded-full bg-blue-500/10 text-blue-400 flex items-center justify-center text-2xl mb-3">
              <i class="fa-solid fa-cloud-arrow-up"></i>
            </div>
            <h3 class="text-sm font-semibold text-white">Click or Drag & Drop your Resume PDF here</h3>
            <p class="text-xs text-gray-400 mt-1">Supports PDF or Plain Text (.pdf, .txt) up to 10MB</p>
            <button onclick="document.getElementById('cv-file-input').click()" class="mt-4 bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs px-5 py-2.5 rounded-xl border border-gray-700">
              Browse File on Computer
            </button>
          </div>
        </div>

        <div class="glass-card p-6 rounded-2xl">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-bold text-white flex items-center space-x-2">
              <i class="fa-solid fa-id-card-clip text-emerald-400"></i>
              <span>Parsed Profile & Fact Grounding Summary</span>
            </h3>
            <div class="flex items-center space-x-3">
              <button onclick="toggleRawJson()" id="btn-toggle-json" class="text-xs text-gray-400 hover:text-white">
                <i class="fa-solid fa-code mr-1"></i> Edit Raw JSON
              </button>
              <button onclick="saveProfile()" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-lg shadow-emerald-600/30">
                <i class="fa-solid fa-floppy-disk mr-1"></i> Save Changes
              </button>
            </div>
          </div>

          <div id="visual-profile-card" class="space-y-4">
            <div class="grid grid-cols-2 gap-4 bg-gray-950 p-4 rounded-xl border border-gray-800/80">
              <div>
                <span class="text-[10px] text-gray-500 uppercase tracking-wider">Candidate Name</span>
                <div id="p-name" class="text-base font-bold text-white mt-0.5">-</div>
                <div id="p-contact" class="text-xs text-gray-400 mt-1">-</div>
              </div>
              <div>
                <span class="text-[10px] text-gray-500 uppercase tracking-wider">Target Locations</span>
                <div id="p-location" class="text-xs text-amber-300 mt-0.5 font-medium">-</div>
                <div id="p-links" class="text-xs text-blue-400 mt-1 space-x-2"></div>
              </div>
            </div>

            <div>
              <span class="text-[10px] text-gray-500 uppercase tracking-wider block mb-2">Verified Core Competencies</span>
              <div id="p-skills" class="flex flex-wrap gap-2"></div>
            </div>

            <div>
              <span class="text-[10px] text-gray-500 uppercase tracking-wider block mb-2">Target Roles</span>
              <div id="p-roles" class="flex flex-wrap gap-2"></div>
            </div>
          </div>

          <div id="raw-json-container" class="mt-4 hidden">
            <label class="block text-xs font-semibold text-gray-400 mb-1">Raw Master Profile JSON (Fact Truth Store)</label>
            <textarea id="profile-json-editor" class="w-full h-96 bg-gray-950 border border-gray-800 rounded-xl p-4 font-mono text-xs text-gray-200 focus:outline-none focus:border-blue-500 leading-relaxed"></textarea>
          </div>
        </div>
      </section>

      <!-- TAB 4: APPLICATION RUNNER -->
      <section id="tab-apply" class="space-y-6 hidden">
        <div class="glass-card p-6 rounded-2xl">
          <h2 class="text-base font-bold text-white mb-2">Targeted Single-Job Application Runner</h2>
          <p class="text-xs text-gray-400 mb-6">Dispatch the full multi-agent pipeline against any single job posting URL with location scoring.</p>
          
          <div class="space-y-4">
            <div>
              <label class="block text-xs font-medium text-gray-300 mb-1">Target Job Opening URL</label>
              <input id="input-job-url" type="url" placeholder="https://boards.greenhouse.io/company/jobs/12345" class="w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500">
            </div>

            <div class="flex items-center space-x-6 py-2">
              <label class="flex items-center space-x-2 cursor-pointer text-xs">
                <input id="chk-dry-run" type="checkbox" checked class="w-4 h-4 rounded bg-gray-900 border-gray-700 text-blue-600 focus:ring-0">
                <span class="text-gray-300">Dry-Run Mode (Pre-Flight Safety Assertion only)</span>
              </label>
              <label class="flex items-center space-x-2 cursor-pointer text-xs">
                <input id="chk-force-manual" type="checkbox" class="w-4 h-4 rounded bg-gray-900 border-gray-700 text-blue-600 focus:ring-0">
                <span class="text-gray-300">Enforce Manual HITL Sign-off</span>
              </label>
            </div>

            <div class="pt-2 flex items-center space-x-3">
              <button onclick="dispatchPipeline()" id="btn-dispatch-pipeline" class="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-6 py-3 rounded-xl transition-all shadow-lg shadow-blue-600/30">
                <i class="fa-solid fa-bolt mr-2"></i> Execute Multi-Agent Pipeline
              </button>
              <button onclick="setSampleMockUrl()" class="bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs px-4 py-3 rounded-xl">
                Use Synthetic Mock ATS Target
              </button>
            </div>
          </div>
        </div>

        <div id="pipeline-result-card" class="glass-card p-6 rounded-2xl hidden">
          <h3 class="text-xs font-bold text-white mb-2 flex items-center space-x-2">
            <i class="fa-solid fa-terminal text-emerald-400"></i>
            <span>Pipeline Execution Output</span>
          </h3>
          <pre id="pipeline-log-output" class="bg-gray-950 p-4 rounded-xl text-[11px] text-gray-300 font-mono overflow-x-auto max-h-96"></pre>
        </div>
      </section>

      <!-- TAB 5: TRACKER -->
      <section id="tab-tracker" class="space-y-6 hidden">
        <div class="glass-card p-6 rounded-2xl">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-base font-bold text-white">Full Application Tracking Ledger</h2>
            <button onclick="loadLedgerTable()" class="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded-lg">
              <i class="fa-solid fa-arrows-rotate mr-1"></i> Refresh
            </button>
          </div>
          <div id="full-ledger-table" class="overflow-x-auto text-xs"></div>
        </div>
      </section>

      <!-- TAB 6: RECRUITER HUB -->
      <section id="tab-recruiter" class="space-y-6 hidden">
        <div class="glass-card p-6 rounded-2xl">
          <h2 class="text-base font-bold text-white mb-2">Recruiter Interaction & Email Classifier</h2>
          <p class="text-xs text-gray-400 mb-6">Test Agent 4 NLP classification on inbound recruiter communications and generate contextual follow-ups.</p>
          
          <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-gray-300 mb-1">Company Name</label>
                <input id="input-recruiter-company" type="text" value="Apex Neural Systems" class="w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-2 text-xs text-white">
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-300 mb-1">Email Subject Line</label>
                <input id="input-recruiter-subject" type="text" value="Invitation to Interview: HR Operations Executive" class="w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-2 text-xs text-white">
              </div>
            </div>

            <div>
              <label class="block text-xs font-medium text-gray-300 mb-1">Email Body Content</label>
              <textarea id="input-recruiter-body" rows="5" class="w-full bg-gray-900 border border-gray-700 rounded-xl p-4 text-xs text-white">Hi Jayanth, thanks for applying for the HR Operations Executive role! We were impressed with your background in HRMS, statutory compliance, and payroll coordination, and would love to schedule a 30-minute discussion. Please choose a slot here: https://calendly.com/apex-recruiting/30min</textarea>
            </div>

            <button onclick="classifyRecruiterEmail()" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-6 py-2.5 rounded-xl shadow-lg shadow-indigo-600/30">
              <i class="fa-solid fa-wand-magic-sparkles mr-1"></i> Classify Intent & Draft Follow-up
            </button>
          </div>
        </div>

        <div id="recruiter-result-card" class="glass-card p-6 rounded-2xl hidden">
          <h3 class="text-xs font-bold text-white mb-3">Classification & Response Assistant</h3>
          <div class="grid grid-cols-3 gap-4 mb-4">
            <div class="p-3 bg-gray-900 rounded-xl border border-gray-800">
              <div class="text-[10px] text-gray-400">Classified Intent</div>
              <div id="res-intent" class="text-sm font-bold text-emerald-400 mt-1">INTERVIEW_REQUEST</div>
            </div>
            <div class="p-3 bg-gray-900 rounded-xl border border-gray-800">
              <div class="text-[10px] text-gray-400">Confidence Score</div>
              <div id="res-confidence" class="text-sm font-bold text-blue-400 mt-1">98%</div>
            </div>
            <div class="p-3 bg-gray-900 rounded-xl border border-gray-800">
              <div class="text-[10px] text-gray-400">Extracted Scheduling Link</div>
              <a id="res-sched-link" href="#" target="_blank" class="text-xs font-medium text-indigo-400 hover:underline truncate block mt-1">None</a>
            </div>
          </div>
          <div>
            <div class="text-xs font-semibold text-gray-300 mb-2">Automated Follow-up Response Draft:</div>
            <textarea id="res-draft-body" rows="6" class="w-full bg-gray-950 border border-gray-800 rounded-xl p-4 text-xs text-gray-200 font-mono"></textarea>
          </div>
        </div>
      </section>

      <!-- TAB 7: COMPLIANCE -->
      <section id="tab-compliance" class="space-y-6 hidden">
        <div class="glass-card p-6 rounded-2xl">
          <h2 class="text-base font-bold text-white mb-2">Data Privacy & GDPR Governance</h2>
          <p class="text-xs text-gray-400 mb-6">User-centric compliance guarantees. Full telemetry transparency and irreversible data deletion.</p>
          
          <div class="grid grid-cols-2 gap-6">
            <div class="p-5 bg-gray-900/60 rounded-xl border border-gray-800 space-y-3">
              <h3 class="text-xs font-bold text-white flex items-center space-x-2">
                <i class="fa-solid fa-file-export text-blue-400"></i>
                <span>Right to Data Portability (GDPR Art. 20)</span>
              </h3>
              <p class="text-[11px] text-gray-400">Export your master profile facts, credential mappings, and full application history as a portable JSON package.</p>
              <button onclick="downloadGdprExport()" class="bg-gray-800 hover:bg-gray-700 text-white text-xs px-4 py-2 rounded-lg">
                <i class="fa-solid fa-download mr-1"></i> Download GDPR Archive
              </button>
            </div>

            <div class="p-5 bg-red-950/20 rounded-xl border border-red-900/40 space-y-3">
              <h3 class="text-xs font-bold text-red-300 flex items-center space-x-2">
                <i class="fa-solid fa-trash-can text-red-400"></i>
                <span>Right to Erasure (GDPR Art. 17)</span>
              </h3>
              <p class="text-[11px] text-gray-400">Permanently erase all tracked application records, generated cover letters, and submission confirmation identifiers.</p>
              <button onclick="purgeGdprData()" class="bg-red-600 hover:bg-red-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-lg shadow-red-600/30">
                <i class="fa-solid fa-triangle-exclamation mr-1"></i> Purge All Records
              </button>
            </div>
          </div>
        </div>
      </section>

    </main>
  </div>

  <script>
    function showToast(message, type = 'success') {
      const container = document.getElementById('toast-container');
      const toast = document.createElement('div');
      toast.className = `pointer-events-auto flex items-center space-x-3 px-4 py-3 rounded-xl border shadow-2xl transition-all duration-300 transform translate-x-10 opacity-0 ${
        type === 'success' ? 'bg-emerald-950/90 border-emerald-500/40 text-emerald-200' :
        type === 'error' ? 'bg-red-950/90 border-red-500/40 text-red-200' :
        'bg-blue-950/90 border-blue-500/40 text-blue-200'
      }`;
      const icon = type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-circle-xmark' : 'fa-circle-info';
      toast.innerHTML = `<i class="fa-solid ${icon} text-base"></i><span class="text-xs font-medium">${message}</span>`;
      container.appendChild(toast);

      setTimeout(() => toast.classList.remove('translate-x-10', 'opacity-0'), 50);
      setTimeout(() => {
        toast.classList.add('translate-x-10', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
      }, 4500);
    }

    function switchTab(tabId) {
      const tabs = ['dashboard', 'scout', 'profile', 'apply', 'tracker', 'recruiter', 'compliance'];
      tabs.forEach(t => {
        const el = document.getElementById(`tab-${t}`);
        if (el) el.classList.add('hidden');
        const navBtn = document.getElementById(`nav-${t}`);
        if (navBtn) {
          navBtn.classList.remove('bg-blue-600/20', 'text-blue-400', 'border', 'border-blue-500/30');
          navBtn.classList.add('text-gray-400');
        }
      });
      const activeEl = document.getElementById(`tab-${tabId}`);
      if (activeEl) activeEl.classList.remove('hidden');
      const activeNav = document.getElementById(`nav-${tabId}`);
      if (activeNav) {
        activeNav.classList.remove('text-gray-400');
        activeNav.classList.add('bg-blue-600/20', 'text-blue-400', 'border', 'border-blue-500/30');
      }

      if (tabId === 'dashboard') loadDashboard();
      if (tabId === 'scout') executeLiveJobSearch();
      if (tabId === 'tracker') loadLedgerTable();
      if (tabId === 'profile') loadProfileData();
    }

    // Live Location-Aware Job Scout
    let discoveredJobs = [];

    async function executeLiveJobSearch() {
      const kw = document.getElementById('scout-keyword').value;
      const locStr = document.getElementById('scout-locations').value;
      const locations = locStr.split(',').map(s => s.trim()).filter(Boolean);

      const btn = document.getElementById('btn-search-jobs');
      btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin mr-1.5"></i> Searching...`;
      btn.disabled = true;

      const container = document.getElementById('scout-results-table');
      container.innerHTML = `<p class="text-blue-400 py-6 text-center animate-pulse"><i class="fa-solid fa-satellite-dish mr-2"></i> Querying live career boards and filtering by location...</p>`;

      try {
        const res = await fetch('/api/jobs/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ keywords: kw, locations: locations })
        });
        const data = await res.json();
        discoveredJobs = data.jobs || [];

        document.getElementById('scout-results-count').innerText = discoveredJobs.length;
        const batchBtn = document.getElementById('btn-batch-apply');
        const selectAllBtn = document.getElementById('btn-select-all');

        if (discoveredJobs.length === 0) {
          container.innerHTML = `<p class="text-gray-500 py-6 text-center">No openings found matching your criteria. Try adjusting keywords or location tags.</p>`;
          batchBtn.classList.add('hidden');
          selectAllBtn.classList.add('hidden');
          return;
        }

        batchBtn.classList.remove('hidden');
        selectAllBtn.classList.remove('hidden');

        let html = `<table class="w-full text-left">
          <thead>
            <tr class="text-gray-400 border-b border-gray-800">
              <th class="py-3 px-2"><input type="checkbox" id="chk-master" onchange="toggleSelectAll(this)"></th>
              <th class="py-3">Company</th>
              <th class="py-3">Job Title</th>
              <th class="py-3">Location Match</th>
              <th class="py-3">Status</th>
              <th class="py-3">Action</th>
            </tr>
          </thead>
          <tbody>`;

        discoveredJobs.forEach((job, idx) => {
          const locClass = job.is_remote ? 'badge-remote' : 'badge-location';
          const statusBadge = job.already_applied ? 
            `<span class="px-2 py-0.5 rounded text-[10px] bg-gray-800 text-gray-400">Already Applied</span>` :
            `<span class="px-2 py-0.5 rounded text-[10px] bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">Ready to Apply</span>`;

          html += `<tr class="border-b border-gray-800/60 hover:bg-gray-800/30">
            <td class="py-3 px-2"><input type="checkbox" class="job-checkbox" value="${job.url}" ${job.already_applied ? 'disabled' : 'checked'} onchange="updateSelectedCount()"></td>
            <td class="py-3 font-bold text-white uppercase text-[11px]">${job.board}</td>
            <td class="py-3 text-gray-200 font-medium">${job.title}</td>
            <td class="py-3"><span class="px-2.5 py-1 rounded-full text-[10px] font-semibold ${locClass}"><i class="fa-solid fa-location-dot mr-1"></i>${job.location}</span></td>
            <td class="py-3">${statusBadge}</td>
            <td class="py-3">
              <a href="${job.url}" target="_blank" class="text-blue-400 hover:underline mr-3"><i class="fa-solid fa-arrow-up-right-from-square"></i> View</a>
              <button onclick="applyDirectUrl('${job.url}')" class="text-emerald-400 hover:text-emerald-300 font-semibold"><i class="fa-solid fa-paper-plane"></i> Apply</button>
            </td>
          </tr>`;
        });

        html += `</tbody></table>`;
        container.innerHTML = html;
        updateSelectedCount();
        showToast(`Discovered ${discoveredJobs.length} openings matching your location preferences!`, 'success');
      } catch (err) {
        container.innerHTML = `<p class="text-red-400 py-4 text-center">Search failed: ${err.message}</p>`;
        showToast("Job search error: " + err.message, 'error');
      } finally {
        btn.innerHTML = `<i class="fa-solid fa-magnifying-glass mr-1.5"></i> Search Live Openings`;
        btn.disabled = false;
      }
    }

    function toggleSelectAll(master) {
      document.querySelectorAll('.job-checkbox:not(:disabled)').forEach(cb => cb.checked = master.checked);
      updateSelectedCount();
    }

    function selectAllScoutJobs() {
      const master = document.getElementById('chk-master');
      master.checked = true;
      toggleSelectAll(master);
    }

    function updateSelectedCount() {
      const selected = document.querySelectorAll('.job-checkbox:checked');
      document.getElementById('selected-count').innerText = selected.length;
    }

    async function autoApplySelected() {
      const selectedCbs = Array.from(document.querySelectorAll('.job-checkbox:checked'));
      const urls = selectedCbs.map(cb => cb.value);
      if (urls.length === 0) {
        showToast("Please select at least one job to apply.", 'info');
        return;
      }

      const dryRun = document.getElementById('scout-dry-run').checked;
      const btn = document.getElementById('btn-batch-apply');
      btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin mr-1.5"></i> Processing ${urls.length} Applications...`;
      btn.disabled = true;

      showToast(`Executing pipeline across ${urls.length} location-filtered jobs...`, 'info');

      try {
        const res = await fetch('/api/jobs/batch-apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_urls: urls, dry_run: dryRun })
        });
        const data = await res.json();
        showToast(`Completed applications for ${data.processed} roles according to location!`, 'success');
        loadDashboard();
        executeLiveJobSearch();
      } catch (err) {
        showToast("Batch application failed: " + err.message, 'error');
      } finally {
        btn.innerHTML = `<i class="fa-solid fa-paper-plane mr-1.5"></i> Auto-Apply to Selected (<span id="selected-count">0</span>)`;
        btn.disabled = false;
      }
    }

    function applyDirectUrl(url) {
      document.getElementById('input-job-url').value = url;
      switchTab('apply');
    }

    // Dashboard Data
    async function loadDashboard() {
      try {
        const res = await fetch('/api/ledger');
        const data = await res.json();
        document.getElementById('stat-total').innerText = data.summary.total_tracked;
        document.getElementById('stat-submitted').innerText = data.summary.submitted;
        document.getElementById('stat-dryrun').innerText = data.summary.dry_run_verified;
        document.getElementById('stat-fit').innerText = `${data.summary.average_match_score}%`;

        const container = document.getElementById('recent-ledger-table');
        if (!data.applications || data.applications.length === 0) {
          container.innerHTML = `<div class="p-6 text-center text-gray-500">No applications tracked yet. Click 'Search Live Openings' to start!</div>`;
          return;
        }

        let html = `<table class="w-full text-left">
          <thead>
            <tr class="text-gray-400 border-b border-gray-800">
              <th class="py-2">Company</th>
              <th class="py-2">Role</th>
              <th class="py-2">Match Score</th>
              <th class="py-2">Status</th>
              <th class="py-2">Last Updated</th>
            </tr>
          </thead>
          <tbody>`;

        data.applications.slice(0, 5).forEach(app => {
          const isSubmitted = app.status === 'SUBMITTED' || app.status === 'APPLIED';
          const badgeClass = isSubmitted ? 'badge-submitted' : 'badge-dryrun';
          html += `<tr class="border-b border-gray-800/40 hover:bg-gray-800/20">
            <td class="py-3 font-semibold text-white">${app.company_name}</td>
            <td class="py-3 text-gray-300">${app.job_title}</td>
            <td class="py-3 font-mono text-blue-400">${(app.relevance_score * 100).toFixed(0)}%</td>
            <td class="py-3"><span class="px-2.5 py-1 rounded-full text-[10px] font-semibold ${badgeClass}">${app.status}</span></td>
            <td class="py-3 text-gray-400">${app.last_updated}</td>
          </tr>`;
        });
        html += `</tbody></table>`;
        container.innerHTML = html;
      } catch (err) {
        console.error(err);
      }
    }

    // Full Ledger Table
    async function loadLedgerTable() {
      try {
        const res = await fetch('/api/ledger');
        const data = await res.json();
        const container = document.getElementById('full-ledger-table');
        if (!data.applications || data.applications.length === 0) {
          container.innerHTML = `<div class="p-6 text-center text-gray-500">No applications recorded in ledger.</div>`;
          return;
        }

        let html = `<table class="w-full text-left">
          <thead>
            <tr class="text-gray-400 border-b border-gray-800">
              <th class="py-3">Company</th>
              <th class="py-3">Job Title</th>
              <th class="py-3">Match</th>
              <th class="py-3">Status</th>
              <th class="py-3">Confirmation / Receipt</th>
              <th class="py-3">Job Link</th>
            </tr>
          </thead>
          <tbody>`;

        data.applications.forEach(app => {
          const isSubmitted = app.status === 'SUBMITTED' || app.status === 'APPLIED';
          const badgeClass = isSubmitted ? 'badge-submitted' : 'badge-dryrun';
          html += `<tr class="border-b border-gray-800/60 hover:bg-gray-800/30">
            <td class="py-3 font-bold text-white">${app.company_name}</td>
            <td class="py-3 text-gray-300">${app.job_title}</td>
            <td class="py-3 font-mono text-cyan-400">${(app.relevance_score * 100).toFixed(1)}%</td>
            <td class="py-3"><span class="px-2.5 py-1 rounded-full text-[10px] font-semibold ${badgeClass}">${app.status}</span></td>
            <td class="py-3 font-mono text-[10px] text-gray-400">${app.confirmation_id || 'N/A'}</td>
            <td class="py-3"><a href="${app.job_url}" target="_blank" class="text-blue-400 hover:underline">Link</a></td>
          </tr>`;
        });
        html += `</tbody></table>`;
        container.innerHTML = html;
      } catch (err) {
        console.error(err);
      }
    }

    // Profile Data
    let currentProfile = null;

    async function loadProfileData() {
      try {
        const res = await fetch('/api/profile');
        currentProfile = await res.json();
        
        document.getElementById('p-name').innerText = `${currentProfile.first_name} ${currentProfile.last_name}`;
        document.getElementById('p-contact').innerText = `${currentProfile.email} • ${currentProfile.phone}`;
        
        const locs = currentProfile.preferred_locations && currentProfile.preferred_locations.length > 0 ?
          currentProfile.preferred_locations.join(' • ') : currentProfile.location;
        document.getElementById('p-location').innerText = locs;
        
        let linkHtml = '';
        if (currentProfile.linkedin_url) linkHtml += `<a href="${currentProfile.linkedin_url}" target="_blank" class="hover:underline"><i class="fa-brands fa-linkedin"></i> LinkedIn</a>`;
        if (currentProfile.github_url) linkHtml += `<a href="${currentProfile.github_url}" target="_blank" class="hover:underline"><i class="fa-brands fa-github"></i> GitHub</a>`;
        document.getElementById('p-links').innerHTML = linkHtml;

        const skillsDiv = document.getElementById('p-skills');
        skillsDiv.innerHTML = (currentProfile.verified_skills || []).map(s => 
          `<span class="px-2.5 py-1 bg-blue-950/60 text-blue-300 border border-blue-800/60 rounded-lg text-xs">${s}</span>`
        ).join('');

        const rolesDiv = document.getElementById('p-roles');
        rolesDiv.innerHTML = (currentProfile.target_roles || []).map(r => 
          `<span class="px-2.5 py-1 bg-gray-800 text-gray-300 rounded-lg text-xs">${r}</span>`
        ).join('');

        document.getElementById('profile-json-editor').value = JSON.stringify(currentProfile, null, 2);
      } catch (err) {
        showToast("Failed to load candidate profile: " + err, 'error');
      }
    }

    function toggleRawJson() {
      const el = document.getElementById('raw-json-container');
      const isHidden = el.classList.contains('hidden');
      if (isHidden) {
        el.classList.remove('hidden');
        document.getElementById('btn-toggle-json').innerHTML = `<i class="fa-solid fa-eye-slash mr-1"></i> Hide Raw JSON`;
      } else {
        el.classList.add('hidden');
        document.getElementById('btn-toggle-json').innerHTML = `<i class="fa-solid fa-code mr-1"></i> Edit Raw JSON`;
      }
    }

    async function handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);
      showToast(`Uploading and extracting '${file.name}' with NLP...`, 'info');

      try {
        const res = await fetch('/api/profile/upload-pdf', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (res.ok) {
          showToast(data.message, 'success');
          loadProfileData();
        } else {
          showToast(data.detail || 'Upload failed', 'error');
        }
      } catch (err) {
        showToast("Upload error: " + err.message, 'error');
      }
    }

    const dropZone = document.getElementById('drop-zone');
    if (dropZone) {
      ['dragenter', 'dragover'].forEach(name => {
        dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.add('border-blue-400', 'bg-blue-950/20'); });
      });
      ['dragleave', 'drop'].forEach(name => {
        dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.remove('border-blue-400', 'bg-blue-950/20'); });
      });
      dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files[0]) {
          document.getElementById('cv-file-input').files = files;
          handleFileUpload({ target: { files: files } });
        }
      });
    }

    async function saveProfile() {
      try {
        const text = document.getElementById('profile-json-editor').value;
        const parsed = JSON.parse(text);
        const res = await fetch('/api/profile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parsed)
        });
        const result = await res.json();
        if (res.ok) {
          showToast("Profile truth store saved successfully!", 'success');
          loadProfileData();
        } else {
          showToast("Validation Error: " + result.detail, 'error');
        }
      } catch (err) {
        showToast("JSON syntax error: " + err.message, 'error');
      }
    }

    async function triggerMockRun() {
      const btn = document.getElementById('btn-quick-sim');
      btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> Running Simulation...`;
      btn.disabled = true;

      try {
        const res = await fetch('/api/pipeline/run-mock', { method: 'POST' });
        const data = await res.json();
        showToast("Synthetic Mock ATS Simulation completed! 4 agents executed successfully.", 'success');
        loadDashboard();
      } catch (err) {
        showToast("Simulation error: " + err.message, 'error');
      } finally {
        btn.innerHTML = `<i class="fa-solid fa-play"></i> Run E2E Simulation`;
        btn.disabled = false;
      }
    }

    function setSampleMockUrl() {
      document.getElementById('input-job-url').value = "http://127.0.0.1:8899/greenhouse/job/gh-78901";
      document.getElementById('chk-dry-run').checked = true;
    }

    async function dispatchPipeline() {
      const url = document.getElementById('input-job-url').value;
      if (!url) {
        showToast("Please provide a target job URL.", 'error');
        return;
      }
      const dryRun = document.getElementById('chk-dry-run').checked;
      const forceManual = document.getElementById('chk-force-manual').checked;

      const btn = document.getElementById('btn-dispatch-pipeline');
      btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin mr-2"></i> Executing Multi-Agent Pipeline...`;
      btn.disabled = true;

      const resultCard = document.getElementById('pipeline-result-card');
      const logOut = document.getElementById('pipeline-log-output');
      resultCard.classList.remove('hidden');
      logOut.innerText = "Connecting to Agents 1, 2, 3, and 4...\\nRunning discovery, location compatibility, and tailoring...";

      try {
        const res = await fetch('/api/pipeline/apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_url: url, dry_run: dryRun, force_manual: forceManual })
        });
        const data = await res.json();
        logOut.innerText = JSON.stringify(data, null, 2);
        showToast("Pipeline execution completed!", 'success');
      } catch (err) {
        logOut.innerText = "Pipeline execution error: " + err.message;
        showToast("Pipeline failed: " + err.message, 'error');
      } finally {
        btn.innerHTML = `<i class="fa-solid fa-bolt mr-2"></i> Execute Multi-Agent Pipeline`;
        btn.disabled = false;
      }
    }

    async function classifyRecruiterEmail() {
      const company = document.getElementById('input-recruiter-company').value;
      const subject = document.getElementById('input-recruiter-subject').value;
      const body = document.getElementById('input-recruiter-body').value;

      try {
        const res = await fetch('/api/recruiter/classify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ company_name: company, subject: subject, body: body })
        });
        const data = await res.json();
        document.getElementById('recruiter-result-card').classList.remove('hidden');
        document.getElementById('res-intent').innerText = data.intent;
        document.getElementById('res-confidence').innerText = `${(data.confidence * 100).toFixed(0)}%`;
        const linkElem = document.getElementById('res-sched-link');
        if (data.scheduling_link) {
          linkElem.innerText = data.scheduling_link;
          linkElem.href = data.scheduling_link;
        } else {
          linkElem.innerText = "No scheduling link detected";
          linkElem.href = "#";
        }
        document.getElementById('res-draft-body').value = data.draft_response;
        showToast("Classified email as " + data.intent, 'success');
      } catch (err) {
        showToast("Classification failed: " + err.message, 'error');
      }
    }

    async function downloadGdprExport() {
      window.open('/api/compliance/export', '_blank');
      showToast("Downloading GDPR telemetry export archive...", 'info');
    }

    async function purgeGdprData() {
      if (confirm("Are you sure you want to permanently erase all application records and history? This cannot be undone.")) {
        const res = await fetch('/api/compliance/purge', { method: 'DELETE' });
        const data = await res.json();
        showToast(data.status, 'success');
        loadDashboard();
      }
    }

    window.onload = () => {
      loadDashboard();
    };
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    uvicorn.run("autonomous_job_agent.web.app:app", host="0.0.0.0", port=8000, reload=False)
