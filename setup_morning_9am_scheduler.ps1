# PowerShell script to register Windows Scheduled Task for Morning 9:00 AM Auto-Apply
# Runs daily at 09:00 AM sharp to apply to top-matching jobs

$ErrorActionPreference = "Stop"

$TaskName = "AryaMorning9AMJobApplier"
$ProjectDir = "C:\Users\jjaya\.gemini\antigravity\scratch\autonomous-job-agent"
$RunnerBat = Join-Path $ProjectDir "run_morning_9am_cycle.bat"
$LogFile = Join-Path $ProjectDir "storage\morning_9am_scheduler.log"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Setting up Windows Scheduled Task: $TaskName" -ForegroundColor Cyan
Write-Host " Schedule: Daily at 09:00 AM" -ForegroundColor Cyan
Write-Host " Target Batch Runner: $RunnerBat" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Ensure storage directory exists
$StorageDir = Join-Path $ProjectDir "storage"
if (-not (Test-Path $StorageDir)) {
    New-Item -ItemType Directory -Path $StorageDir -Force | Out-Null
}

# Register daily 9:00 AM scheduled task using schtasks.exe
Write-Host "Registering task with schtasks.exe (Daily at 09:00)..." -ForegroundColor Yellow
$TR_Arg = "`"$RunnerBat`""
& schtasks.exe /Create /SC DAILY /ST 09:00 /TN "$TaskName" /TR "$TR_Arg" /F | Out-Host

Write-Host "`n[SUCCESS] Windows Task '$TaskName' registered successfully!" -ForegroundColor Green
Write-Host "  Trigger Time: Daily at 09:00 AM (Morning)" -ForegroundColor Green
Write-Host "  Execution Log: $LogFile" -ForegroundColor Green
Write-Host "  To test manually now: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Cyan
Write-Host "  To check status: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Cyan
