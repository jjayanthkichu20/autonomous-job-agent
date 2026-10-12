"""Hostinger / cPanel Phusion Passenger WSGI entry point for Autonomous Job Platform."""

import os
import sys

# Ensure current project directory is in sys.path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Adapt FastAPI ASGI app to WSGI for Hostinger Passenger Python
from a2wsgi import ASGIMiddleware
from autonomous_job_agent.web.app import app

application = ASGIMiddleware(app)
