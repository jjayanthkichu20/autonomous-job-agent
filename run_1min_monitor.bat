@echo off
REM ============================================================
REM  1-Minute Autonomous Job Radar & Morning 9 AM Applier
REM ============================================================
cd /d "%~dp0"
set PYTHONPATH=.

echo [Arya AI] Launching 1-Minute Job Radar...
python monitor_1min.py
