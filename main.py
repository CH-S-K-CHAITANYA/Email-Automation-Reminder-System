"""
main.py
-------
Entry point for the Email Automation & Reminder System.
Orchestrates all modules: reading contacts, personalizing emails,
scheduling reminders, sending (or simulating), logging, and reporting.

Run modes:
  python main.py            → Dry-run (simulation, no real emails sent)
  python main.py --live     → Live mode (sends real emails via Gmail SMTP)
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add src to path for module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.contact_reader import load_contacts, load_reminders
from src.template_engine import TemplateEngine
from src.email_sender import EmailSender
from src.status_tracker import StatusTracker
from src.report_generator import generate_report, print_report_preview
from src.scheduler import simulate_scheduled_reminders

# ─────────────────────────────────────────────
# SETUP LOGGING
# ─────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/email_log.txt"),     # Save to file
        logging.StreamHandler(sys.stdout)              # Print to terminal
    ]
)
logger = logging.getLogger("main")


def print_banner():
    """Print a welcome banner."""
    print("\n" + "═" * 60)
    print("  📧  EMAIL AUTOMATION & REMINDER SYSTEM")
    print("  Python Automation Project | Student GitHub Portfolio")
    print("═" * 60)
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    # ─────────────────────────────────────────
    # STEP 0: Load environment variables
    # ─────────────────────────────────────────
    load_dotenv()  # Reads from .env file

    # Check if running in live or dry-run mode
    live_mode = "--live" in sys.argv
    dry_run = not live_mode

    # Read credentials from environment variables
    sender_email = os.getenv("SENDER_EMAIL", "demo@gmail.com")
    sender_password = os.getenv("SENDER_PASSWORD", "")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    # Allow .env to override dry_run
    if os.getenv("DRY_RUN", "True").lower() == "false":
        dry_run = False

    print_banner()
    mode_label = "🔵 DRY-RUN (Simulation)" if dry_run else "🟢 LIVE (Real Emails)"
    print(f"\n  Mode: {mode_label}")
    print(f"  Sender: {sender_email}\n")

    # ─────────────────────────────────────────
    # STEP 1: Load contacts and reminders
    # ─────────────────────────────────────────
    print("📂 Loading data files...")
    contacts = load_contacts("data/contacts.csv")
    reminders = load_reminders("data/reminders.csv")
    print(f"  ✅ Loaded {len(contacts)} contacts, {len(reminders)} reminders")

    # ─────────────────────────────────────────
    # STEP 2: Display reminder schedule
    # ─────────────────────────────────────────
    simulate_scheduled_reminders(reminders)

    # ─────────────────────────────────────────
    # STEP 3: Initialize template engine
    # ─────────────────────────────────────────
    print("\n🎨 Initializing template engine...")
    engine = TemplateEngine(templates_dir="templates")

    # ─────────────────────────────────────────
    # STEP 4: Initialize email sender
    # ─────────────────────────────────────────
    sender = EmailSender(
        sender_email=sender_email,
        sender_password=sender_password,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        dry_run=dry_run
    )

    # ─────────────────────────────────────────
    # STEP 5: Send emails to all contacts
    # ─────────────────────────────────────────
    email_subject = "📅 Reminder: Your Upcoming Event"

    # Use lambda functions to render templates per contact
    results = sender.send_bulk(
        contacts=contacts,
        subject=email_subject,
        html_template_rendered=lambda c: engine.render("reminder_template.html", {
            "name": c["name"], "event": c["event"],
            "event_date": c["event_date"], "department": c["department"],
            "custom_message": c["custom_message"]
        }),
        txt_template_rendered=lambda c: engine.render("reminder_template.txt", {
            "name": c["name"], "event": c["event"],
            "event_date": c["event_date"], "department": c["department"],
            "custom_message": c["custom_message"]
        })
    )

    # ─────────────────────────────────────────
    # STEP 6: Track and display results
    # ─────────────────────────────────────────
    tracker = StatusTracker()
    tracker.add_results(results)
    tracker.print_summary()

    # ─────────────────────────────────────────
    # STEP 7: Print detail table
    # ─────────────────────────────────────────
    print_report_preview(results)

    # ─────────────────────────────────────────
    # STEP 8: Generate CSV report
    # ─────────────────────────────────────────
    report_path = generate_report(results, output_dir="outputs")

    print(f"\n✅ Campaign complete! Report saved at: {report_path}")
    print("📁 Check logs/ folder for detailed email_log.txt\n")


if __name__ == "__main__":
    main()