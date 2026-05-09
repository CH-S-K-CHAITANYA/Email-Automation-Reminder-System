"""
email_sender.py
---------------
Handles SMTP connection and email dispatching.
Supports dry-run mode for safe testing without sending real emails.
"""

import smtplib
import logging
import time
import re

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)


def is_valid_email(email: str) -> tuple[bool, str]:
    """
    Validate email address format and reject dummy/test emails.
    
    Args:
        email (str): Email address to validate.
    
    Returns:
        tuple[bool, str]: (is_valid, error_message)
    """
    # Check for empty email
    if not email or not isinstance(email, str):
        return False, "Email is empty or invalid"
    
    email = email.strip()
    
    # Basic email format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Email format is invalid"
    
    email_lower = email.lower()
    username, domain = email_lower.split('@')
    
    # Reject test/dummy email patterns
    test_patterns = ['.test', 'test.', '_test', 'test_', 'dummy', 'fake', 'sample', 'demo']
    
    for pattern in test_patterns:
        if pattern in username or pattern in domain:
            return False, f"Email appears to be a dummy/test email (contains '{pattern}')"
    
    # Reject known dummy domains
    dummy_domains = [
        'test.com', 'test.in', 'example.com', 'dummy.com', 
        'fake.com', 'sample.com', 'demo.com'
    ]
    
    if domain in dummy_domains:
        return False, f"Email domain '{domain}' is a dummy/test domain"
    
    # Reject *.test domain (TLD for testing)
    if domain.endswith('.test'):
        return False, "Email domain '.test' is not a valid production email domain"
    
    return True, ""


class EmailSender:
    """
    Manages SMTP connection and sends personalized emails.
    """

    def __init__(
        self,
        sender_email: str,
        sender_password: str,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        dry_run: bool = True
    ):

        self.sender_email = sender_email
        self.sender_password = sender_password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.dry_run = dry_run

        mode = "DRY-RUN (simulation)" if dry_run else "LIVE (real emails)"
        logger.info(f"EmailSender initialized in {mode} mode")

    def create_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        html_content: str,
        txt_content: str
    ) -> MIMEMultipart:

        msg = MIMEMultipart("alternative")

        msg["Subject"] = subject
        msg["From"] = f"Automation System <{self.sender_email}>"
        msg["To"] = f"{recipient_name} <{recipient_email}>"

        # Extra headers
        msg["Reply-To"] = self.sender_email
        msg["X-Mailer"] = "Python Email Automation System"

        # Plain text first
        part1 = MIMEText(txt_content, "plain")
        part2 = MIMEText(html_content, "html")

        msg.attach(part1)
        msg.attach(part2)

        return msg

    def send_email(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        html_content: str,
        txt_content: str
    ) -> dict:

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ─────────────────────────────────────
        # EMAIL VALIDATION
        # ─────────────────────────────────────
        is_valid, error_msg = is_valid_email(recipient_email)
        
        if not is_valid:
            logger.warning(
                f"[REJECTED] Invalid email for {recipient_name}: "
                f"{recipient_email} - {error_msg}"
            )
            
            print(
                f"  ⚠️  [REJECTED] Invalid email → "
                f"{recipient_name} ({recipient_email}): {error_msg}"
            )
            
            return {
                "status": "rejected",
                "recipient_name": recipient_name,
                "recipient_email": recipient_email,
                "subject": subject,
                "timestamp": timestamp,
                "message": f"Email rejected: {error_msg}"
            }

        # ─────────────────────────────────────
        # DRY RUN
        # ─────────────────────────────────────
        if self.dry_run:

            logger.info(
                f"[DRY-RUN] Would send to: "
                f"{recipient_name} <{recipient_email}>"
            )

            print(
                f"  ✅ [DRY-RUN] Simulated email → "
                f"{recipient_name} ({recipient_email})"
            )

            return {
                "status": "simulated",
                "recipient_name": recipient_name,
                "recipient_email": recipient_email,
                "subject": subject,
                "timestamp": timestamp,
                "message": "Email simulated successfully"
            }

        # ─────────────────────────────────────
        # LIVE SEND
        # ─────────────────────────────────────
        try:

            msg = self.create_email(
                recipient_email,
                recipient_name,
                subject,
                html_content,
                txt_content
            )

            # Fresh SMTP connection for each email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:

                server.ehlo()

                # Secure TLS connection
                server.starttls()

                server.ehlo()

                # Login
                server.login(
                    self.sender_email,
                    self.sender_password
                )

                # Send email
                response = server.sendmail(
                    self.sender_email,
                    recipient_email,
                    msg.as_string()
                )

                # SMTP refused recipients
                if response:
                    raise Exception(
                        f"SMTP refused recipient: {response}"
                    )

            logger.info(
                f"[SENT] Email sent to: "
                f"{recipient_name} <{recipient_email}>"
            )

            print(
                f"  ✅ [SENT] Email delivered → "
                f"{recipient_name} ({recipient_email})"
            )

            return {
                "status": "sent",
                "recipient_name": recipient_name,
                "recipient_email": recipient_email,
                "subject": subject,
                "timestamp": timestamp,
                "message": "Email sent successfully"
            }

        except smtplib.SMTPAuthenticationError:

            error_msg = (
                "Authentication failed. "
                "Check Gmail App Password."
            )

            logger.error(
                f"[FAILED] Auth error for "
                f"{recipient_email}: {error_msg}"
            )

            print(
                f"  ❌ [FAILED] Auth error → "
                f"{recipient_email}"
            )

            return {
                "status": "failed",
                "recipient_name": recipient_name,
                "recipient_email": recipient_email,
                "subject": subject,
                "timestamp": timestamp,
                "message": error_msg
            }

        except smtplib.SMTPRecipientsRefused:

            error_msg = (
                f"Recipient refused: {recipient_email}"
            )

            logger.error(f"[FAILED] {error_msg}")

            print(
                f"  ❌ [FAILED] Recipient refused → "
                f"{recipient_email}"
            )

            return {
                "status": "failed",
                "recipient_name": recipient_name,
                "recipient_email": recipient_email,
                "subject": subject,
                "timestamp": timestamp,
                "message": error_msg
            }

        except Exception as e:

            error_msg = str(e)

            logger.error(
                f"[FAILED] Unexpected error sending to "
                f"{recipient_email}: {error_msg}"
            )

            print(
                f"  ❌ [FAILED] Error → "
                f"{recipient_email}: {error_msg}"
            )

            return {
                "status": "failed",
                "recipient_name": recipient_name,
                "recipient_email": recipient_email,
                "subject": subject,
                "timestamp": timestamp,
                "message": error_msg
            }

    def send_bulk(
        self,
        contacts: list,
        subject: str,
        html_template_rendered: callable,
        txt_template_rendered: callable
    ) -> list[dict]:

        results = []

        total = len(contacts)

        print(
            f"\n📤 Starting email dispatch for "
            f"{total} contacts...\n"
        )

        for i, contact in enumerate(contacts, 1):

            print(
                f"  [{i}/{total}] "
                f"Processing: {contact['name']}"
            )

            html = html_template_rendered(contact)
            txt = txt_template_rendered(contact)

            result = self.send_email(
                recipient_email=contact["email"],
                recipient_name=contact["name"],
                subject=subject,
                html_content=html,
                txt_content=txt
            )

            results.append(result)

            # Delay to avoid Gmail throttling
            time.sleep(2)

        return results