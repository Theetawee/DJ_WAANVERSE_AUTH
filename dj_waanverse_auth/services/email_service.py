# flake8: noqa: E203

import logging
import random
import string
import threading
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Union

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.validators import EmailValidator
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from dj_waanverse_auth.security.utils import (
    get_device,
    get_ip_address,
    get_location_from_ip,
)
from dj_waanverse_auth.settings import auth_config

logger = logging.getLogger(__name__)

Account = get_user_model()


class EmailTemplate(Enum):
    """Enum for email templates to ensure consistency."""

    VERIFICATION = "verify_email"
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    LOGIN_ALERT = "login_alert"
    ACCOUNT_LOCKED = "account_locked"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"


class EmailPriority(Enum):
    """Email priority levels for handling different types of emails."""

    HIGH = "high"  # For critical emails like security alerts
    MEDIUM = "medium"  # For important but not critical emails
    LOW = "low"  # For marketing and non-critical emails


@dataclass
class EmailConfig:
    """Configuration settings for emails."""

    BATCH_SIZE = auth_config.email_batch_size  # Number of emails to send in one batch
    RETRY_ATTEMPTS = (
        auth_config.email_retry_attempts
    )  # Number of retry attempts for failed emails
    RETRY_DELAY = auth_config.email_retry_delay  # Delay in seconds between retries
    MAX_RECIPIENTS = (
        auth_config.email_max_recipients
    )  # Maximum number of recipients in one email
    THREAD_POOL_SIZE = (
        auth_config.email_thread_pool_size
    )  # Number of threads for sending emails
    VERIFICATION_EMAIL_SUBJECT = auth_config.verification_email_subject
    VERIFICATION_EMAIL_EXPIRATION_TIME = (
        f"{auth_config.verification_email_code_expiry_in_minutes} minutes"
    )
    MFA_CHANGED_EMAIL_SUBJECT = auth_config.mfa_changed_email_subject


class EmailValidationError(ValidationError):
    """Custom exception for email validation errors."""

    pass


class EmailService:
    """Production-ready email service handling all email-related functionality."""

    def __init__(self, request=None):
        """Initialize email service with configuration."""
        self.config = EmailConfig()
        self.email_validator = EmailValidator()
        self._connection = None
        self.request = request

    @property
    def connection(self):
        """Lazy loading of email connection."""
        if self._connection is None:
            self._connection = get_connection(
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                fail_silently=False,
            )
        return self._connection

    class EmailThread(threading.Thread):
        """Thread for asynchronous email sending."""

        def __init__(self, service_instance, emails):
            self.service = service_instance
            self.emails = emails
            super().__init__()

        def run(self):
            """Execute email sending in thread."""
            try:
                with self.service.connection as connection:
                    connection.send_messages(self.emails)
            except Exception as e:
                logger.error(f"Thread email sending failed: {str(e)}")

    def validate_email(
        self,
        email_address: str,
        check_uniqueness: bool = False,
        check_disposable: bool = True,
        check_blacklist: bool = True,
    ) -> dict:
        """
        Comprehensive email validation.

        Args:
            email: Email address to validate
            check_uniqueness: Whether to check if email is already in use
            check_disposable: Whether to check against disposable email domains
            check_blacklist: Whether to check against blacklisted patterns

        Returns:
            dict: Dictionary with 'email' and 'error' keys

        Raises:
            EmailValidationError: If validation fails
        """
        try:
            self.email_validator(email_address)

            email_address = email_address.lower().strip()
            local_part, domain = email_address.split("@")

            if check_blacklist and domain in auth_config.blacklisted_domains:
                return {"email": email_address, "error": "This email is not allowed."}

            # Check disposable email services
            if check_disposable and domain in auth_config.disposable_email_domains:
                return {
                    "email": email_address,
                    "error": "This email is disposable. Please use a different email.",
                }

            # Check uniqueness if required
            if check_uniqueness:

                if Account.objects.filter(email_address=email_address).exists():

                    return {
                        "email": email_address,
                        "error": "This email is already in use.",
                    }

            return {"email": email_address, "error": None}
        except ValidationError as e:
            logger.error(f"Email validation error: {str(e)}")
            return {"email": email_address, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in email validation: {str(e)}")
            return {"email": email_address, "error": str(e)}

    def prepare_email_message(
        self,
        subject: str,
        template_name: Union[str, EmailTemplate],
        context: dict,
        recipient_list: Union[str, List[str]],
        priority: EmailPriority = EmailPriority.MEDIUM,
        attachments: Optional[List] = None,
    ) -> EmailMultiAlternatives:
        """
        Prepare an email message with both HTML and plain text versions.

        Args:
            subject: Email subject
            template_name: Name of the template or EmailTemplate enum
            context: Context data for the template
            recipient_list: List of recipient email addresses
            priority: Email priority level
            attachments: List of attachment files

        Returns:
            Prepared email message
        """
        if isinstance(template_name, EmailTemplate):
            template_name = template_name.value

        template_path = f"emails/{template_name}.html"

        context.update(
            {
                "site_name": auth_config.platform_name,
                "company_address": auth_config.platform_address,
                "support_email": auth_config.platform_contact_email,
            }
        )

        html_content = render_to_string(template_path, context)
        plain_content = strip_tags(html_content)

        # Create message
        if isinstance(recipient_list, str):
            recipient_list = [recipient_list]

        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
            connection=self.connection,
        )

        # Add HTML alternative
        msg.attach_alternative(html_content, "text/html")

        # Add attachments
        if attachments:
            for attachment in attachments:
                msg.attach_file(attachment)

        # Set priority headers
        if priority == EmailPriority.HIGH:
            msg.extra_headers["X-Priority"] = "1"

        return msg

    def send_email(
        self,
        subject: str,
        template_name: Union[str, EmailTemplate],
        context: dict,
        recipient_list: Union[str, List[str]],
        priority: EmailPriority = EmailPriority.MEDIUM,
        attachments: Optional[List] = None,
        async_send: bool = True,
    ) -> bool:
        """
        Send an email with proper error handling and logging.

        Args:
            subject: Email subject
            template_name: Template name or EmailTemplate enum
            context: Template context
            recipient_list: Recipients
            priority: Email priority
            attachments: Email attachments
            async_send: Whether to send asynchronously

        Returns:
            bool: Whether the email was sent successfully
        """
        try:
            # Validate recipients
            if isinstance(recipient_list, str):
                recipient_list = [recipient_list]

            if len(recipient_list) > self.config.MAX_RECIPIENTS:
                raise ValueError(
                    f"Too many recipients (max {self.config.MAX_RECIPIENTS})"
                )

            # Prepare email message
            email_message = self.prepare_email_message(
                subject, template_name, context, recipient_list, priority, attachments
            )

            # Send email
            if async_send and auth_config.email_threading_enabled:
                self.EmailThread(self, [email_message]).start()
            else:
                email_message.send()

            logger.info(
                f"Email sent successfully to {len(recipient_list)} recipients: {subject}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send email: {str(e)}",
                extra={
                    "subject": subject,
                    "template": template_name,
                    "recipients": len(recipient_list),
                },
                exc_info=True,
            )
            return False

    def send_verification_email(self, email: str, verification_code: str) -> bool:
        """Send email verification code."""
        from dj_waanverse_auth.models import VerificationCode

        existing_verification = VerificationCode.objects.filter(email=email).first()
        if existing_verification:
            existing_verification.delete()

        with transaction.atomic():
            new_verification = VerificationCode.objects.create(
                email=email, code=verification_code
            )
            new_verification.save()
            context = {
                "code": verification_code,
                "expiry_time": self.config.VERIFICATION_EMAIL_EXPIRATION_TIME,
            }
            return self.send_email(
                subject=self.config.VERIFICATION_EMAIL_SUBJECT,
                template_name=EmailTemplate.VERIFICATION,
                context=context,
                recipient_list=email,
                priority=EmailPriority.HIGH,
            )

    def send_password_reset_email(self, email: str, reset_token: str) -> bool:
        """Send password reset email."""
        context = {
            "reset_token": reset_token,
            "expiry_hours": settings.PASSWORD_RESET_EXPIRY_HOURS,
        }
        return self.send_email(
            subject="Reset Your Password",
            template_name=EmailTemplate.PASSWORD_RESET,
            context=context,
            recipient_list=email,
            priority=EmailPriority.HIGH,
        )

    def send_login_alert(self, email: str) -> bool:
        """Send new login alert.

        Args:
            email: Recipient email
        """
        if not self.request:
            raise ValueError("Request object is required")
        if auth_config.send_login_alert_emails:
            ip_address = get_ip_address(self.request)
            context = {
                "device_info": get_device(self.request),
                "location_info": get_location_from_ip(ip_address=ip_address),
                "timestamp": timezone.now(),
                "ip_address": ip_address,
            }
            return self.send_email(
                subject=auth_config.login_alert_email_subject,
                template_name=EmailTemplate.LOGIN_ALERT,
                context=context,
                recipient_list=email,
                priority=EmailPriority.HIGH,
            )
        else:
            logger.warning("Login alert email sending is disabled.")
            return False

    def send_account_locked_notification(self, email: str) -> bool:
        """Send account locked notification."""
        context = {
            "support_email": settings.SUPPORT_EMAIL,
            "locked_time": timezone.now(),
        }
        return self.send_email(
            subject="Account Security Alert",
            template_name=EmailTemplate.ACCOUNT_LOCKED,
            context=context,
            recipient_list=email,
            priority=EmailPriority.HIGH,
        )

    def send_mfa_change_notification(self, email_address: str, change_type) -> bool:
        """Send MFA enabled notification.
        type: 'enable' or 'disable'
        """
        if auth_config.email_security_notifications_enabled:
            if change_type not in ["enable", "disable"]:
                raise ValueError("Type must be 'enable' or 'disable'.")
            context = {
                "mfa_time": timezone.now(),
            }

            return self.send_email(
                subject=self.config.MFA_CHANGED_EMAIL_SUBJECT,
                template_name=(
                    EmailTemplate.MFA_ENABLED
                    if change_type == "enable"
                    else EmailTemplate.MFA_DISABLED
                ),
                context=context,
                recipient_list=email_address,
                priority=EmailPriority.HIGH,
            )
        else:
            logger.warning("MFA enabled notification email sending is disabled.")
            return False

    def send_batch_emails(
        self,
        template_name: Union[str, EmailTemplate],
        context: dict,
        recipient_list: List[str],
        subject: str,
    ) -> tuple[int, int]:
        """
        Send batch emails efficiently.

        Returns:
            tuple: (success_count, failure_count)
        """
        success_count = 0
        failure_count = 0

        # Process in batches
        for i in range(0, len(recipient_list), self.config.BATCH_SIZE):
            batch = recipient_list[i : i + self.config.BATCH_SIZE]
            messages = [
                self.prepare_email_message(subject, template_name, context, [recipient])
                for recipient in batch
            ]

            try:
                # Send batch
                with self.connection as connection:
                    connection.send_messages(messages)
                success_count += len(batch)
            except Exception as e:
                logger.error(f"Batch email sending failed: {str(e)}")
                failure_count += len(batch)

        return success_count, failure_count

    @staticmethod
    def generate_verification_code(
        length: int = auth_config.email_verification_code_length,
        alphanumeric: bool = auth_config.email_verification_code_is_alphanumeric,
    ) -> str:
        """
        Generate a random verification code.

        Args:
            length (int): The length of the verification code. Default is 6.
            alphanumeric (bool): If True, includes both letters and numbers. Default is False.

        Returns:
            str: Generated verification code.
        """
        if length <= 0:
            raise ValueError("Length must be greater than 0.")

        characters = string.digits
        if alphanumeric:
            characters += string.ascii_letters

        return "".join(random.choices(characters, k=length))
