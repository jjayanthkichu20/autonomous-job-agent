"""Continuous 1-Minute Job Radar & Morning 9:00 AM Auto-Applier

1. Scans job boards & verified feeds every 1 minute (60s).
2. Maintains the best-matching unapplied openings strictly on top.
3. Automatically triggers morning applications at 09:00 AM daily.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time

from morning_9am_apply import run_morning_apply

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("1min_job_monitor")

REPO_DIR = Path(__file__).resolve().parent
DOCS_DATA_DIR = REPO_DIR / "docs" / "data"
STORAGE_DIR = REPO_DIR / "storage"
JOBS_FILE = DOCS_DATA_DIR / "jobs.json"
STATE_FILE = STORAGE_DIR / "monitor_state.json"


def scan_and_rank():
    """Reads jobs, ranks best unapplied on top, and saves state."""
    if not JOBS_FILE.exists():
        return
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    # Sort best unapplied on top
    jobs.sort(key=lambda x: (not x.get("already_applied", False), x.get("match_score", 0)), reverse=True)
    data["jobs"] = jobs
    data["count"] = len(jobs)

    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    unapplied_count = sum(1 for j in jobs if not j.get("already_applied"))
    top_score = jobs[0].get("match_score") if jobs else 0
    top_title = jobs[0].get("title") if jobs else "N/A"
    top_company = jobs[0].get("company") if jobs else "N/A"

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "last_scan_utc": datetime.now(timezone.utc).isoformat(),
        "last_scan_local": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        "total_jobs": len(jobs),
        "unapplied_jobs": unapplied_count,
        "top_match_score": top_score,
        "top_match": f"{top_title} at {top_company}",
        "interval_seconds": 60,
        "status": "ACTIVE_SCANNING"
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    logger.info(f"[1-Min Scan] Checked feed. Total: {len(jobs)} | Unapplied: {unapplied_count} | Top: [{top_score}%] {top_title} ({top_company})")


def main_loop():
    logger.info("=" * 60)
    logger.info("🟢 Starting 1-Minute Job Radar & 9:00 AM Morning Dispatcher")
    logger.info("   - Scan Interval: Every 60 seconds (1 minute)")
    logger.info("   - Ranking: Best match scores ranked strictly to the top")
    logger.info("   - Scheduled Apply: Daily at 09:00 AM")
    logger.info("=" * 60)

    last_morning_applied_day = None

    while True:
        try:
            scan_and_rank()

            now = datetime.now()
            # Check if 9:00 AM (between 09:00 and 09:01)
            today_str = now.strftime("%Y-%m-%d")
            if now.hour == 9 and now.minute == 0 and last_morning_applied_day != today_str:
                logger.info("🌅 09:00 AM REACHED! Triggering morning job application batch...")
                run_morning_apply(batch_size=5, dry_run=False)
                last_morning_applied_day = today_str

        except Exception as e:
            logger.error(f"Error during scan loop: {e}")

        # Wait 60 seconds (1 minute)
        time.sleep(60)


if __name__ == "__main__":
    main_loop()
