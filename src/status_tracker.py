"""
status_tracker.py
-----------------
Tracks and summarizes the status of sent/failed/simulated emails.
"""

import logging

logger = logging.getLogger(__name__)


class StatusTracker:
    """
    Tracks email campaign results and provides summary statistics.
    """

    def __init__(self):
        self.results = []

    def add_results(self, results: list[dict]):
        """Add a list of email result records."""
        self.results.extend(results)
        logger.info(f"Added {len(results)} results to tracker. Total: {len(self.results)}")

    def get_summary(self) -> dict:
        """
        Compute summary statistics for the campaign.

        Returns:
            dict: Summary with counts for each status.
        """
        total = len(self.results)
        sent = sum(1 for r in self.results if r["status"] == "sent")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        rejected = sum(1 for r in self.results if r["status"] == "rejected")
        simulated = sum(1 for r in self.results if r["status"] == "simulated")

        summary = {
            "total": total,
            "sent": sent,
            "failed": failed,
            "rejected": rejected,
            "simulated": simulated,
            "success_rate": f"{((sent + simulated) / total * 100):.1f}%" if total > 0 else "0%"
        }
        return summary

    def print_summary(self):
        """Print a formatted summary to the terminal."""
        summary = self.get_summary()
        print("\n" + "=" * 50)
        print("📊  EMAIL CAMPAIGN SUMMARY")
        print("=" * 50)
        print(f"  Total Processed : {summary['total']}")
        print(f"  ✅ Sent         : {summary['sent']}")
        print(f"  🔵 Simulated    : {summary['simulated']}")
        print(f"  ⚠️  Rejected     : {summary['rejected']}")
        print(f"  ❌ Failed       : {summary['failed']}")
        print(f"  📈 Success Rate : {summary['success_rate']}")
        print("=" * 50 + "\n")

    def get_failed(self) -> list[dict]:
        """Return only failed email records."""
        return [r for r in self.results if r["status"] == "failed"]