from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from dj_waanverse_auth.models import LoginCode

from django.core.mail.backends.base import BaseEmailBackend
from mailersend import MailerSendClient, EmailBuilder
from django.conf import settings
from django.utils.html import strip_tags

User = get_user_model()


class AuthenticationBackend(BaseBackend):
    """
    Custom authentication backend for login using email + one-time code.
    """

    def authenticate(
        self,
        request,
        email_address=None,
        username=None,
        code=None,
        password=None,
        **kwargs
    ):
        if username and password:
            return super().authenticate(request, username=username, password=password)
        if not email_address:
            raise ValidationError(("Email address is required for authentication."))
        if not code:
            raise ValidationError(("Verification code is required for authentication."))

        try:
            user = User.objects.get(email_address=email_address)
        except User.DoesNotExist:
            raise ValidationError(_("No account found with that email address."))

        login_code = LoginCode.objects.filter(account=user, code=code.strip()).first()
        if not login_code:
            raise ValidationError(_("Invalid verification code."))

        if login_code.is_expired():
            login_code.delete()  # Prevent reuse of expired codes
            raise ValidationError(_("The verification code has expired."))

        # Code is valid → delete it to enforce one-time use
        login_code.delete()
        print("Authenticated user:", user)
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class EmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = settings.MAILERSEND_API_KEY
        default_from_email = settings.DEFAULT_FROM_EMAIL
        default_from_name = getattr(settings, "DEFAULT_FROM_NAME", "No Reply")

        if not api_key:
            raise ValueError("MAILERSEND_API_KEY is not set")
        if not default_from_email:
            raise ValueError("DEFAULT_FROM_EMAIL is not set")

        send_count = 0
        try:
            ms = MailerSendClient(api_key=api_key)

            for message in email_messages:
                # Only one recipient
                recipient = message.to[
                    0
                ]  # assume dict with "email" and optional "name"
                recipient_email = (
                    recipient.get("email") if isinstance(recipient, dict) else recipient
                )
                recipient_name = (
                    recipient.get("name", "") if isinstance(recipient, dict) else ""
                )

                # Get HTML if available
                template_content = message.body or ""
                for alt, mimetype in getattr(message, "alternatives", []):
                    if mimetype == "text/html":
                        template_content = alt
                        break

                # Fallback for text body
                text_body = message.body or strip_tags(template_content)

                # Build and send email
                email = (
                    EmailBuilder()
                    .from_email(default_from_email, default_from_name)
                    .to_many([{"email": recipient_email, "name": recipient_name}])
                    .subject(message.subject)
                    .html(template_content)
                    .text(text_body)
                    .build()
                )

                ms.emails.send(email)
                send_count += 1

            return send_count

        except Exception as e:
            if not self.fail_silently:
                raise e
            raise
