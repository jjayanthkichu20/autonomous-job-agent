@echo off
REM ============================================================
REM  Morning 9:00 AM Autonomous Job Application Dispatcher
REM ============================================================
cd /d "%~dp0"
set PYTHONPATH=.

echo [Morning 9 AM Auto-Pilot] Starting scheduled application run...
python morning_9am_apply.py --batch=5 >> "storage\morning_9am_scheduler.log" 2>&1

echo [Morning 9 AM Auto-Pilot] Finished at %DATE% %TIME%
