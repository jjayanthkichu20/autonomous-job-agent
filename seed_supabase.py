"""CLI Utility to Seed & Sync Local Autonomous Job Agent Data into Supabase

Usage:
    python seed_supabase.py --url https://xyz.supabase.co --key eyJhbGciOi...
    or (if already saved in storage/supabase_config.json):
    python seed_supabase.py
"""

import argparse
import sys
from pathlib import Path

# Add repo to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from autonomous_job_agent.core.supabase_db import supabase_db


def main():
    parser = argparse.ArgumentParser(description="Seed and Sync Autonomous Job Agent data to Supabase.")
    parser.add_argument("--url", help="Supabase Project URL (e.g. https://xyz.supabase.co)")
    parser.add_argument("--key", help="Supabase Anon/Public Key or Service Role Key")
    parser.add_argument("--test-only", action="store_true", help="Test connection only without uploading data")
    args = parser.parse_args()

    if args.url and args.key:
        supabase_db.save_config(args.url, args.key)
        print(f"Configured Supabase URL: {args.url}")

    if not supabase_db.is_configured():
        print("ERROR: Supabase URL and Key are not configured.")
        print("Please provide them via flags:")
        print("  python seed_supabase.py --url https://your-project.supabase.co --key your-anon-key")
        sys.exit(1)

    print(f"\n[1/3] Testing connection to Supabase ({supabase_db.url})...")
    conn_result = supabase_db.test_connection()
    if not conn_result.get("connected"):
        print(f"FAILED: {conn_result.get('error')}")
        print("\nTIP: Make sure you created the tables first by running 'supabase_schema.sql' in your Supabase SQL Editor.")
        sys.exit(1)

    print("SUCCESS: Connected to Supabase!")

    if args.test_only:
        print("Test only flag provided. Exiting.")
        sys.exit(0)

    print("\n[2/3] Seeding local jobs, candidate profile, and application ledger to Supabase...")
    sync_res = supabase_db.sync_all_local_data()

    if sync_res.get("success"):
        details = sync_res.get("details", {})
        print("\n[3/3] SYNCHRONIZATION COMPLETE!")
        print(f"  - Candidate Profile: {'Synced' if details.get('profile') else 'Failed/Skipped'}")
        print(f"  - Jobs Synced: {details.get('jobs_synced', 0)}")
        print(f"  - Applications Synced: {details.get('applications_synced', 0)}")
        print("\nYour website is now wired directly to your Supabase cloud database!")
    else:
        print(f"ERROR during sync: {sync_res.get('error')}")


if __name__ == "__main__":
    main()
