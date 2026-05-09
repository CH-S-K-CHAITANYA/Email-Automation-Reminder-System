"""
contact_reader.py
-----------------
Reads and validates the contacts CSV file.
Returns a list of contact dictionaries for email processing.
"""

import pandas as pd
import logging

# Set up logger for this module
logger = logging.getLogger(__name__)


def _is_send_enabled(value) -> bool:
    """Return whether a contact should be included in campaign sends."""
    if pd.isna(value):
        return True
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"false", "0", "no", "n", "off", "disabled"}


def load_contacts(filepath: str) -> list[dict]:
    """
    Load contacts from a CSV file and validate required columns.

    Args:
        filepath (str): Path to the contacts CSV file.

    Returns:
        list[dict]: List of contact records as dictionaries.
    """
    # Define which columns must exist in the CSV
    required_columns = {"id", "name", "email", "department", "event", "event_date", "custom_message"}

    try:
        # Read the CSV file using pandas
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} contacts from {filepath}")

        # Check if all required columns are present
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns in contacts CSV: {missing}")

        # Drop rows where email is missing (can't send email without it)
        original_count = len(df)
        df = df.dropna(subset=["email"])
        dropped = original_count - len(df)

        if dropped > 0:
            logger.warning(f"Dropped {dropped} contacts with missing email addresses.")

        # Optional dashboard-managed flag for choosing who receives campaigns.
        if "send_enabled" not in df.columns:
            df["send_enabled"] = True

        before_filter = len(df)
        df = df[df["send_enabled"].apply(_is_send_enabled)]
        skipped = before_filter - len(df)

        if skipped > 0:
            logger.info(f"Skipped {skipped} contacts marked send_enabled=False.")

        # Convert to list of dictionaries for easy iteration
        contacts = df.to_dict(orient="records")
        return contacts

    except FileNotFoundError:
        logger.error(f"Contact file not found: {filepath}")
        raise
    except Exception as e:
        logger.error(f"Error reading contacts: {e}")
        raise


def load_reminders(filepath: str) -> list[dict]:
    """
    Load reminder schedule data from CSV.

    Args:
        filepath (str): Path to the reminders CSV file.

    Returns:
        list[dict]: List of reminder records.
    """
    try:
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} reminders from {filepath}")
        return df.to_dict(orient="records")
    except FileNotFoundError:
        logger.error(f"Reminders file not found: {filepath}")
        raise
