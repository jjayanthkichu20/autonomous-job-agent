@echo off
REM Autonomous 2-Hour Job Hunter Cycle Runner
cd /d "%~dp0"
set PYTHONPATH=.
".venv\Scripts\python.exe" -m autonomous_job_agent.cli recurring --once --live-submit >> "storage\windows_scheduler.log" 2>&1
