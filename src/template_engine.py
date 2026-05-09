"""
template_engine.py
------------------
Handles email template loading and personalization using Jinja2.
Supports both HTML and plain-text templates.
"""

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import logging
import os

logger = logging.getLogger(__name__)


class TemplateEngine:
    """
    Loads and renders email templates with contact-specific data.
    """

    def __init__(self, templates_dir: str):
        """
        Initialize Jinja2 environment with the templates directory.

        Args:
            templates_dir (str): Path to the folder containing templates.
        """
        self.env = Environment(loader=FileSystemLoader(templates_dir))
        self.templates_dir = templates_dir
        logger.info(f"Template engine initialized with directory: {templates_dir}")

    def render(self, template_filename: str, context: dict) -> str:
        """
        Render a template file with the given context variables.

        Args:
            template_filename (str): Name of the template file (e.g., 'reminder_template.html').
            context (dict): Dictionary of variables to inject into the template.

        Returns:
            str: The rendered template as a string.
        """
        try:
            template = self.env.get_template(template_filename)
            rendered = template.render(context)
            logger.debug(f"Rendered template '{template_filename}' for: {context.get('name', 'Unknown')}")
            return rendered
        except TemplateNotFound:
            logger.error(f"Template not found: {template_filename}")
            raise
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            raise

    def render_for_contact(self, contact: dict, html_template: str, txt_template: str) -> tuple[str, str]:
        """
        Render both HTML and plain-text versions for a specific contact.

        Args:
            contact (dict): Contact record with personalization data.
            html_template (str): HTML template filename.
            txt_template (str): Plain-text template filename.

        Returns:
            tuple[str, str]: (html_content, text_content)
        """
        # Build context from contact data
        context = {
            "name": contact.get("name", "Valued Member"),
            "email": contact.get("email", ""),
            "department": contact.get("department", "N/A"),
            "event": contact.get("event", "Upcoming Event"),
            "event_date": contact.get("event_date", "TBD"),
            "custom_message": contact.get("custom_message", "Please be prepared."),
        }

        html_content = self.render(html_template, context)
        txt_content = self.render(txt_template, context)

        return html_content, txt_content