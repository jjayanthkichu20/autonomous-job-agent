# PowerShell script to register Windows Scheduled Task for 2-Hour Auto-Pilot Job Hunter
# Runs every 2 hours continuously in the background

$ErrorActionPreference = "Stop"

$TaskName = "Arya2HourJobHunter"
$ProjectDir = "C:\Users\jjaya\.gemini\antigravity\scratch\autonomous-job-agent"
$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$LogFile = Join-Path $ProjectDir "storage\windows_scheduler.log"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Setting up Windows Scheduled Task: $TaskName" -ForegroundColor Cyan
Write-Host " Cycle: Every 2 Hours (Daily, 24/7)" -ForegroundColor Cyan
Write-Host " Target Directory: $ProjectDir" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python executable not found at: $PythonExe"
    exit 1
}

# Ensure storage directory exists
$StorageDir = Join-Path $ProjectDir "storage"
if (-not (Test-Path $StorageDir)) {
    New-Item -ItemType Directory -Path $StorageDir -Force | Out-Null
}

# Target Batch runner
$RunnerBat = Join-Path $ProjectDir "run_scheduler_cycle.bat"

# Register 2-hour scheduled task using schtasks.exe
Write-Host "Registering task with schtasks.exe (Hourly, modifier 2)..." -ForegroundColor Yellow
$TR_Arg = "`"$RunnerBat`""
& schtasks.exe /Create /SC HOURLY /MO 2 /TN "$TaskName" /TR "$TR_Arg" /F | Out-Host

Write-Host "`n[SUCCESS] Windows Task '$TaskName' registered successfully!" -ForegroundColor Green
Write-Host "  Interval: Every 2 hours" -ForegroundColor Green
Write-Host "  Log location: $LogFile" -ForegroundColor Green
Write-Host "  To test manually now: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Cyan
Write-Host "  To check status: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Cyan
