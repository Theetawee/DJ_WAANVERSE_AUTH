import logging
import threading
from enum import Enum
from typing import Callable, List, Optional, Union

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from dj_waanverse_auth import settings

logger = logging.getLogger(__name__)

Account = get_user_model()


class EmailPriority(Enum):
    """Email priority levels for handling different types of emails."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EmailService:
    """Production-ready email service for sending individual emails."""

    # Simple thread tracking
    _active_threads = 0
    _thread_lock = threading.Lock()

    def __init__(self, request=None):
        """Initialize email service with configuration."""
        self._connection = None
        self.request = request

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

    class EmailThread(threading.Thread):
        """Simple thread for sending a single email."""

        def __init__(self, email_message, callback=None):
            super().__init__()  # Initialize the thread properly first
            self.email_message = email_message
            self.callback = callback
            self.daemon = True  # Set daemon mode after initialization

        def run(self):
            """Send a single email in a thread."""
            success = False
            try:
                connection = get_connection(
                    username=django_settings.EMAIL_HOST_USER,
                    password=django_settings.EMAIL_HOST_PASSWORD,
                    fail_silently=False,
                )

                # Send the email with this connection
                self.email_message.connection = connection
                self.email_message.send()
                success = True

            except Exception as e:
                logger.error(f"Email sending failed: {str(e)}", exc_info=True)
            finally:
                with EmailService._thread_lock:
                    EmailService._active_threads -= 1

                if self.callback:
                    try:
                        self.callback(success)
                    except Exception as e:
                        logger.error(f"Email callback error: {str(e)}")

    def _validate_recipients(self, recipient: Union[str, List[str]]) -> List[str]:
        """Validate and normalize recipients."""
        if isinstance(recipient, str):
            recipients = [recipient] if recipient else []
        else:
            recipients = [r for r in recipient if r]

        if not recipients:
            logger.warning("No valid recipients provided for email")
            return []

        return recipients

    def _prepare_email_context(self, context: dict) -> dict:
        """Prepare the email context with standard variables."""
        email_context = context.copy()
        email_context.update(
            {
                "site_name": settings.platform_name,
                "company_address": settings.platform_address,
                "support_email": settings.platform_contact_email,
            }
        )
        return email_context

    def _create_email_message(
        self, subject: str, template_name: str, context: dict, recipients: List[str]
    ) -> EmailMultiAlternatives:
        """Create the email message with content."""
        template_path = (
            f"emails/{template_name}.html"
            if not template_name.endswith(".html")
            else template_name
        )
        html_content = render_to_string(template_path, context)
        plain_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_content,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=recipients,
            connection=self.connection,
        )
        email.attach_alternative(html_content, "text/html")
        return email

    def _prepare_email(
        self,
        subject: str,
        template_name: str,
        context: dict,
        recipients: List[str],
        priority: EmailPriority,
        attachment: Optional[str] = None,
    ) -> EmailMultiAlternatives:
        """Prepare the email message with all necessary configurations."""
        email_context = self._prepare_email_context(context)
        email = self._create_email_message(
            subject, template_name, email_context, recipients
        )

        if attachment:
            email.attach_file(attachment)

        if priority == EmailPriority.HIGH:
            email.extra_headers["X-Priority"] = "1"

        return email

    def _handle_async_send(
        self,
        email: EmailMultiAlternatives,
        recipients: List[str],
        callback: Optional[Callable],
    ) -> bool:
        """Handle asynchronous email sending."""
        with self._thread_lock:
            self._active_threads += 1
        thread = self.EmailThread(email, callback)
        thread.start()
        logger.info(f"Email queued for async sending to {recipients}")
        return True

    def _handle_sync_send(
        self,
        email: EmailMultiAlternatives,
        recipients: List[str],
        callback: Optional[Callable],
    ) -> bool:
        """Handle synchronous email sending."""
        email.send()
        logger.info(f"Email sent synchronously to {recipients}")
        if callback:
            callback(True)
        return True

    def send_email(
        self,
        subject: str,
        template_name: str,
        context: dict,
        recipient: Union[str, List[str]],
        priority: EmailPriority = EmailPriority.MEDIUM,
        attachment: Optional[str] = None,
        async_send: bool = True,
        callback: Optional[Callable] = None,
    ) -> bool:
        """Send a single email with proper error handling."""
        try:
            recipients = self._validate_recipients(recipient)
            if not recipients:
                return False

            email = self._prepare_email(
                subject, template_name, context, recipients, priority, attachment
            )

            if async_send and settings.email_threading_enabled:
                return self._handle_async_send(email, recipients, callback)
            return self._handle_sync_send(email, recipients, callback)

        except Exception as e:
            logger.error(
                f"Failed to prepare/send email: {str(e)}",
                extra={
                    "subject": subject,
                    "template": template_name,
                    "recipient": recipient,
                },
                exc_info=True,
            )
            if callback:
                try:
                    callback(False)
                except Exception as cb_err:
                    logger.error(f"Email callback error: {str(cb_err)}")
            return False

    @classmethod
    def get_active_thread_count(cls):
        """Get the current number of active email threads."""
        with cls._thread_lock:
            return cls._active_threads
