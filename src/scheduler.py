"""
scheduler.py
------------
Simulates scheduled email reminders.
In a real production system, you would use cron jobs or APScheduler.
Here, we use the 'schedule' library for demonstration.
"""

import schedule
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def schedule_job(job_function, run_time: str, label: str = "Email Job"):
    """
    Schedule a job to run at a specific time (HH:MM format).

    Args:
        job_function: The function to call when scheduled.
        run_time (str): Time string like '09:00'.
        label (str): Human-readable label for logging.
    """
    schedule.every().day.at(run_time).do(job_function)
    logger.info(f"Scheduled '{label}' at {run_time} daily")
    print(f"  ⏰ Scheduled '{label}' → runs at {run_time}")


def run_scheduled_jobs(max_seconds: int = 10):
    """
    Run the scheduler loop for a limited time (for demo purposes).
    In production, this would run indefinitely.

    Args:
        max_seconds (int): How many seconds to run the scheduler demo.
    """
    print(f"\n⏱️  Scheduler running for {max_seconds} seconds (demo mode)...")
    print("    In production, this runs continuously as a background service.\n")

    start = time.time()
    while time.time() - start < max_seconds:
        schedule.run_pending()
        time.sleep(1)

    print("  ✅ Scheduler demo completed.\n")


def simulate_scheduled_reminders(reminders: list[dict]):
    """
    Display a simulation of what would be scheduled in production.

    Args:
        reminders (list[dict]): List of reminder records from CSV.
    """
    print("\n📅 REMINDER SCHEDULE SIMULATION:")
    print("-" * 60)
    print(f"{'REMINDER ID':<12} {'CONTACT ID':<12} {'TYPE':<22} {'TIME':<10} {'STATUS'}")
    print("-" * 60)
    for r in reminders:
        print(f"{r['reminder_id']:<12} {str(r['contact_id']):<12} "
              f"{r['reminder_type']:<22} {r['send_time']:<10} {r['status']}")
    print("-" * 60)
    print(f"\n  Total reminders scheduled: {len(reminders)}")