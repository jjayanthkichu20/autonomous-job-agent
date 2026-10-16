@echo off
title Arya Autonomous Job Agent
cd /d "%~dp0"
echo ========================================================
echo   Launching Arya by Mentoria - Autonomous Job Agent
echo ========================================================
echo Starting local web server on port 8000...
start "" "C:\Users\jjaya\.gemini\antigravity\scratch\autonomous-job-agent\.venv\Scripts\python.exe" -m uvicorn autonomous_job_agent.web.app:app --host 127.0.0.1 --port 8000
timeout /t 3 /nobreak >nul
echo Opening application in your default browser...
start http://127.0.0.1:8000
echo ========================================================
echo   Application is running at http://127.0.0.1:8000
echo ========================================================
