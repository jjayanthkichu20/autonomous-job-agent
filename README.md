# Autonomous Multi-Agent Job Application Suite

Production-grade, secure multi-agent automation platform designed to discover job openings, synthesize verified ATS-optimized resumes, submit applications with Human-in-the-Loop (HITL) safety gates, and coordinate recruiter communications.

---

## Architecture Overview

1. **Agent 1 — Job Search & Scraper:** Discovers postings via direct ATS endpoints (Greenhouse, Lever) or HTML career portals, normalizes metadata, applies 64-bit SimHash deduplication, and scores relevance using multi-factor rubric matching against candidate profiles.
2. **Agent 2 — CV & Cover Letter Customizer:** Generates ATS-optimized documents (Markdown, Typst PDF, Word) anchored strictly in a candidate master truth store with verifiable claim attribution, zero hallucination guardrails, and transparent diff reports.
3. **Agent 3 — Application Executor:** Performs semantic form mapping, pre-flight review generation, dry-run assertions, atomic form submission, and live session handover for CAPTCHA/2FA friction.
4. **Agent 4 — Outreach & Notification Coordinator:** Classifies inbound recruiter communications (interviews, assessments, rejections, offers), parses scheduling links, and drafts contextual follow-ups.

---

## Directory Structure

```
autonomous-job-agent/
├── .venv/                                # Isolated virtual environment
├── sample_candidate_profile.json         # Master candidate truth store
├── autonomous_job_agent/
│   ├── core/
│   │   ├── config.py                     # System configuration & thresholds
│   │   ├── models.py                     # Pydantic domain models
│   │   ├── security.py                   # AES-256 envelope encryption & PII scrubber
│   │   └── dedup.py                      # 64-bit SimHash & URL canonicalizer
│   ├── agents/
│   │   ├── agent1_scraper/               # Crawling, normalization & relevance scoring
│   │   ├── agent2_customizer/            # Fact grounding, ATS tailoring & diff engine
│   │   ├── agent3_executor/              # Form mapping, HITL gate & submission engine
│   │   └── agent4_outreach/              # Email intent classifier & scheduling assistant
│   ├── mock_ats/                         # Built-in synthetic Greenhouse & Lever server
│   ├── orchestration/                    # Multi-agent coordination pipeline
│   └── cli.py                            # Interactive CLI tool
├── tests/                                # Full test suite
└── storage/
    └── artifacts/                        # Generated CV variants & execution logs
```

---

## Quickstart & CLI Commands

### 1. Run the Complete 4-Agent Simulation (Mock ATS)
Spins up the internal mock ATS server, executes discovery, relevance scoring, grounded tailoring, pre-flight form mapping, atomic submission, and follow-up generation:
```bash
.\.venv\Scripts\python.exe -m autonomous_job_agent.cli run-mock-e2e
```

### 2. Run the Test Suite
```bash
$env:PYTHONPATH="."
.\.venv\Scripts\pytest.exe -v tests/
```

### 3. Test Agent 4 Email Classifier
```bash
.\.venv\Scripts\python.exe -m autonomous_job_agent.cli parse-email
```

### 4. Run Against a Live Job Posting (Dry-Run by Default)
```bash
.\.venv\Scripts\python.exe -m autonomous_job_agent.cli pipeline --url "https://boards.greenhouse.io/company/jobs/12345"
```
*(Add `--live-submit` only when explicitly intending to perform live network submission)*

---

## Interactive Web Platform & Live Deployment

### Start Local Web Platform Server
```bash
.\.venv\Scripts\python.exe -m uvicorn autonomous_job_agent.web.app:app --host 127.0.0.1 --port 8000
```
Open your browser at `http://localhost:8000` to access the live single-page dashboard.

### Containerized Cloud Deployment (Docker)
```bash
docker compose up -d --build
```
The application will be accessible at port `8000` with persistent volume storage for ledger and CV artifacts.

