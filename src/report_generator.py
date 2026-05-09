"""
report_generator.py
-------------------
Generates CSV reports from email campaign results.
"""

import pandas as pd
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)


def generate_report(results: list[dict], output_dir: str = "outputs") -> str:
    """
    Save campaign results to a timestamped CSV report.

    Args:
        results (list[dict]): List of email result dictionaries.
        output_dir (str): Directory to save the report.

    Returns:
        str: Path to the generated report file.
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"email_report_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)

    # Convert to DataFrame and save
    df = pd.DataFrame(results)

    # Reorder columns for readability
    column_order = ["timestamp", "status", "recipient_name", "recipient_email", "subject", "message"]
    df = df[column_order]

    df.to_csv(filepath, index=False)
    logger.info(f"Report saved: {filepath}")
    print(f"\n📄 Report generated: {filepath}")

    return filepath


def print_report_preview(results: list[dict]):
    """Print a preview of results in the terminal."""
    print("\n📋 DETAILED RESULTS:")
    print("-" * 80)
    print(f"{'NAME':<20} {'EMAIL':<30} {'STATUS':<12} {'TIMESTAMP'}")
    print("-" * 80)
    for r in results:
        print(f"{r['recipient_name']:<20} {r['recipient_email']:<30} {r['status']:<12} {r['timestamp']}")
    print("-" * 80)