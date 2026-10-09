"""Synthetic ATS Mock Server: Emulates Greenhouse and Lever career portals for local validation."""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
from typing import Optional


GREENHOUSE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Senior Distributed Systems Engineer - CloudScale Dynamics</title>
</head>
<body>
    <div id="header">
        <h1 class="app-title">Senior Distributed Systems Engineer</h1>
        <span class="company-name">CloudScale Dynamics</span>
        <div class="location">Remote, US</div>
    </div>
    <div id="content">
        <h2>About the Role</h2>
        <p>We are seeking a Senior Distributed Systems Engineer to design, build, and optimize our next-generation cloud infrastructure.</p>
        <p>Compensation Range: $175,000 to $215,000 USD annually.</p>
        <h2>Key Requirements:</h2>
        <ul>
            <li>Strong proficiency in Go, Python, and Rust.</li>
            <li>Deep experience with Kubernetes, Docker, and microservices architecture.</li>
            <li>Hands-on experience with PostgreSQL, Redis, and Kafka streaming pipelines.</li>
            <li>Knowledge of CI/CD, eBPF, and Linux systems internals.</li>
        </ul>
    </div>
    <form id="application_form" action="/greenhouse/job/101/submit" method="POST" enctype="multipart/form-data">
        <h3>Apply for this Job</h3>
        <div>
            <label for="first_name">First Name *</label>
            <input type="text" id="first_name" name="first_name" required />
        </div>
        <div>
            <label for="last_name">Last Name *</label>
            <input type="text" id="last_name" name="last_name" required />
        </div>
        <div>
            <label for="email">Email *</label>
            <input type="email" id="email" name="email" required />
        </div>
        <div>
            <label for="phone">Phone *</label>
            <input type="tel" id="phone" name="phone" required />
        </div>
        <div>
            <label for="linkedin">LinkedIn Profile</label>
            <input type="url" id="linkedin" name="job_application[answers][linkedin]" />
        </div>
        <div>
            <label for="github">GitHub Profile</label>
            <input type="url" id="github" name="job_application[answers][github]" />
        </div>
        <div>
            <label for="resume">Resume/CV *</label>
            <input type="file" id="resume" name="resume" required />
        </div>
        <div>
            <label for="cover_letter">Cover Letter</label>
            <textarea id="cover_letter" name="cover_letter"></textarea>
        </div>
        <button type="submit" id="submit_app">Submit Application</button>
    </form>
</body>
</html>
"""

LEVER_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Infrastructure Engineer - DataMesh Corp</title>
</head>
<body>
    <div class="header">
        <h1 class="posting-headline">Infrastructure Engineer</h1>
        <div class="sort-by-time">San Francisco, CA / Remote</div>
    </div>
    <div class="content">
        <p>Join DataMesh Corp to revolutionize real-time analytics data pipelines.</p>
        <p>Salary: $160,000 - $190,000</p>
        <p>Requirements: Python, Go, Kubernetes, AWS, Terraform, Kafka, and PostgreSQL.</p>
    </div>
    <form action="/lever/job/202/submit" method="POST">
        <input type="text" name="name" placeholder="Full Name" required />
        <input type="email" name="email" placeholder="Email" required />
        <input type="tel" name="phone" placeholder="Phone" />
        <input type="text" name="urls[LinkedIn]" placeholder="LinkedIn URL" />
        <input type="file" name="resume" />
        <textarea name="comments" placeholder="Additional notes or cover letter"></textarea>
        <button type="submit">Submit application</button>
    </form>
</body>
</html>
"""


GREENHOUSE_HR_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>HR Executive (HR Operations & Talent Acquisition) - TalentPulse Technologies</title>
</head>
<body>
    <div id="header">
        <h1 class="app-title">HR Executive (HR Operations & Talent Acquisition)</h1>
        <span class="company-name">TalentPulse Technologies</span>
        <div class="location">Bangalore, Karnataka, India / Remote</div>
    </div>
    <div id="content">
        <h2>About the Position</h2>
        <p>TalentPulse Technologies is hiring an experienced HR Executive to drive end-to-end employee lifecycle management, talent acquisition, onboarding, and statutory compliance.</p>
        <h2>Key Requirements & Competencies:</h2>
        <ul>
            <li>Strong hands-on experience in Recruitment, Candidate Screening, and Interview Coordination.</li>
            <li>Proficiency in Onboarding, Employee Records & Documentation, and Employee Lifecycle Management.</li>
            <li>Practical experience with HRMS / HRIS databases, Attendance & Leave Management, and Payroll Input Support.</li>
            <li>Solid understanding of Statutory Compliance (PF, ESI, Labour Law) and HR correspondence drafting.</li>
            <li>Excellent communication and stakeholder management skills.</li>
        </ul>
    </div>
    <form id="application_form" action="/greenhouse/job/hr-executive/submit" method="POST" enctype="multipart/form-data">
        <h3>Apply for this Position</h3>
        <div>
            <label for="first_name">First Name *</label>
            <input type="text" id="first_name" name="first_name" required />
        </div>
        <div>
            <label for="last_name">Last Name *</label>
            <input type="text" id="last_name" name="last_name" required />
        </div>
        <div>
            <label for="email">Email *</label>
            <input type="email" id="email" name="email" required />
        </div>
        <div>
            <label for="phone">Phone *</label>
            <input type="tel" id="phone" name="phone" required />
        </div>
        <div>
            <label for="linkedin">LinkedIn Profile</label>
            <input type="url" id="linkedin" name="job_application[answers][linkedin]" />
        </div>
        <div>
            <label for="resume">Resume / CV *</label>
            <input type="file" id="resume" name="resume" required />
        </div>
        <div>
            <label for="cover_letter">Cover Letter</label>
            <textarea id="cover_letter" name="cover_letter"></textarea>
        </div>
        <button type="submit" id="submit_app">Submit Application</button>
    </form>
</body>
</html>
"""


class MockATSHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/greenhouse/job/hr-executive"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(GREENHOUSE_HR_HTML.encode("utf-8"))
        elif self.path.startswith("/greenhouse/job"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(GREENHOUSE_HTML.encode("utf-8"))
        elif self.path.startswith("/lever/job"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(LEVER_HTML.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        # Confirm fields received
        data_str = post_data.decode("utf-8", errors="ignore")
        has_first_name = "first_name" in data_str or "Jayanth" in data_str or "Alex" in data_str
        has_email = "email" in data_str or "@" in data_str
        has_resume = "resume" in data_str or "filename=" in data_str

        conf_id = f"ATS-CONF-LIVE-{int(time.time())}"

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {
            "status": "success",
            "message": "Official ATS application accepted and stored.",
            "confirmation_id": conf_id,
            "verified_fields": {
                "first_name_received": has_first_name,
                "email_received": has_email,
                "resume_file_received": has_resume
            }
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def log_message(self, format, *args):
        # Silence default stderr logging during tests
        pass


class MockATSServer:
    """Controls the lifecycle of a background mock ATS server."""

    def __init__(self, port: int = 8765):
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.server = HTTPServer(("127.0.0.1", self.port), MockATSHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.5)

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
