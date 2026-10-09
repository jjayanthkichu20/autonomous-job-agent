# Multi-stage production container for Autonomous Job Platform
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY autonomous_job_agent/ autonomous_job_agent/
COPY sample_candidate_profile.json .
COPY my_profile.json .

# Create volume mount for persistent storage & ledger
RUN mkdir -p /app/storage/artifacts
VOLUME ["/app/storage"]

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Start production server
CMD ["uvicorn", "autonomous_job_agent.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
