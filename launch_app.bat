@echo off
title Autonomous Job Application Platform Launcher
cd /d "C:\Users\jjaya\.gemini\antigravity\scratch\autonomous-job-agent"

echo ===================================================
echo   Autonomous Job Platform - Launching System
echo ===================================================
echo.

:: Check if server is already running on port 8000
netstat -ano | findstr :8000 | findstr LISTENING >nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Web server is already running on port 8000.
) else (
    echo [INFO] Starting Python Web Server on port 8000...
    start /b "" ".\.venv\Scripts\python.exe" -m uvicorn autonomous_job_agent.web.app:app --host 127.0.0.1 --port 8000
    timeout /t 3 /nobreak >nul
)

:: Start cloudflared tunnel if not already running
tasklist /fi "imagename eq cloudflared.exe" | findstr /i "cloudflared.exe" >nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Cloudflare Tunnel is already active.
) else (
    echo [INFO] Starting Cloudflare Tunnel...
    if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
        start /b "" "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:8000
    )
)

echo.
echo Opening browser to http://localhost:8000 ...
start "" "http://localhost:8000"

echo [SUCCESS] App launched successfully!
timeout /t 2 >nul
exit
