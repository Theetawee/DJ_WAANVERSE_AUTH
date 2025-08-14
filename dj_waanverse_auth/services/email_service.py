import logging
from typing import Union, List

from django.conf import settings as django_settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """Simple email service for sending emails using Django's EmailMultiAlternatives."""

    def __init__(self):
        """Initialize email service with lazy connection."""
        self._connection = None

    @property
    def connection(self):
        """Lazy loading of email connection."""
        if self._connection is None:
            self._connection = get_connection(
                username=django_settings.EMAIL_HOST_USER,
                password=django_settings.EMAIL_HOST_PASSWORD,
                fail_silently=False,
            )
        return self._connection

    def send_email(
        self,
        subject: str,
        template_name: str,
        context: dict,
        recipient: Union[str, List[str]],
    ) -> bool:
        """
        Send an email with both plain text and HTML content.

        Args:
            subject: Email subject.
            template_name: Path to HTML template.
            context: Context for rendering template.
            recipient: Single email or list of emails.
            html_template: Optional separate HTML template.

        Returns:
            True if email was sent successfully, False otherwise.
        """
        if isinstance(recipient, str):
            recipients = [recipient]
        else:
            recipients = [r for r in recipient if r]

        if not recipients:
            logger.warning("No valid recipients provided for email")
            return False

        try:
            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to=recipients,
                connection=self.connection,
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            logger.info(f"Email sent to {recipients}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False
