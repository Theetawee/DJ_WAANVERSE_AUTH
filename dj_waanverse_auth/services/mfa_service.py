import hashlib
import logging
import secrets
from base64 import urlsafe_b64encode

import pyotp
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from dj_waanverse_auth.config.settings import auth_config
from dj_waanverse_auth.models import MultiFactorAuth
from dj_waanverse_auth.services.email_service import EmailService

logger = logging.getLogger(__name__)


class MFAHandler:
    """Reusable class for handling MFA functionality."""

    def __init__(self, user):
        """
        Initialize the MFAHandler with a user.
        :param user: The user object.
        """
        self.user = user
        self.mfa = self.get_mfa()
        self.fernet = Fernet(self._derive_key())

    def _derive_key(self):
        """
        Derive a 32-byte key from Django's SECRET_KEY using SHA256.
        :return: A 32-byte base64-encoded key for Fernet encryption.
        """
        hash_key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        return urlsafe_b64encode(hash_key)

    def get_mfa(self):
        """Get or create the MFA record for the user."""
        mfa, created = MultiFactorAuth.objects.get_or_create(account=self.user)
        return mfa

    def is_mfa_enabled(self):
        """Check if MFA is enabled for the user."""
        return self.mfa.activated

    def generate_secret(self):
        """Generate and save a new MFA secret for the user."""
        if self.mfa.secret_key:
            raw_secret = self.get_decoded_secret()

        else:
            raw_secret = pyotp.random_base32()
            encoded_secret = self.fernet.encrypt(raw_secret.encode()).decode()
            self.mfa.secret_key = encoded_secret
            self.mfa.save()

        return raw_secret

    def activate_mfa(self):
        """Activate MFA for the user."""
        try:
            with transaction.atomic():
                self.mfa.activated = True
                self.mfa.activated_at = now()
                self.mfa.save()

                self.set_recovery_codes()
                if (
                    auth_config.email_security_notifications_enabled
                    and self.user.can_receive_emails
                ):
                    email_manager = EmailService()
                    email_manager.send_email(
                        subject="Account MFA Activated",
                        template_name="emails/mfa_enabled.html",
                        recipient=self.user.email_address,
                        context={"user": self.user},
                    )
        except Exception as e:
            logger.error(f"Error activating MFA: {str(e)}")

    def get_decoded_secret(self):
        """Decode the stored secret key."""
        if not self.mfa.secret_key:
            raise ValueError("No MFA secret found.")
        try:
            return self.fernet.decrypt(self.mfa.secret_key.encode()).decode()
        except Exception as e:
            logger.error(f"Error decrypting MFA secret: {str(e)}")
            raise e

    def get_provisioning_uri(self):
        """
        Get the provisioning URI for the user's MFA setup.
        This is used to generate a QR code for authenticator apps.
        """
        raw_secret = self.get_decoded_secret()
        issuer_name = auth_config.mfa_issuer
        return pyotp.totp.TOTP(raw_secret).provisioning_uri(
            name=(
                self.user.email_address
                if self.user.email_address
                else self.user.username if self.user.username else ""
            ),
            issuer_name=issuer_name,
        )

    def verify_token(self, token: str) -> bool:
        """
        Verify an MFA token provided by the user.
        :param token: The TOTP token to verify.
        :return: True if the token is valid, False otherwise.
        """
        raw_secret = self.get_decoded_secret()
        totp = pyotp.TOTP(raw_secret)
        is_valid = totp.verify(token)
        if not is_valid:
            is_valid = self._verify_recovery_code(token)
        if auth_config.mfa_debug_code is not None:
            if token == auth_config.mfa_debug_code:
                is_valid = True

        return is_valid

    def disable_mfa(self):
        """Disable MFA for the user."""
        try:
            with transaction.atomic():
                self.mfa.activated = False
                self.mfa.activated_at = None
                self.mfa.secret_key = None
                self.mfa.recovery_codes = None
                self.mfa.save()
                if (
                    auth_config.email_security_notifications_enabled
                    and self.user.can_receive_emails
                ):
                    email_manager = EmailService()
                    email_manager.send_mfa_change_notification(
                        self.user.email_address, "disable"
                    )
        except Exception as e:
            logger.error(f"Error disabling MFA: {str(e)}")
            raise e

    def generate_recovery_codes(self):
        """Generate recovery codes for the user and encrypt them."""
        count = auth_config.mfa_recovery_codes_count

        codes = [str(secrets.randbelow(10**7)).zfill(7) for _ in range(count)]

        encrypted_codes = [
            self.fernet.encrypt(code.encode()).decode() for code in codes
        ]

        self.mfa.recovery_codes = encrypted_codes
        self.mfa.save()

        return codes

    def set_recovery_codes(self):
        """Set encrypted recovery codes for the user."""
        recovery_codes = self.generate_recovery_codes()
        encrypted_codes = [
            self.fernet.encrypt(code.encode()).decode() for code in recovery_codes
        ]
        self.mfa.recovery_codes = encrypted_codes
        self.mfa.save()

    def get_recovery_codes(self):
        """Decrypt and get recovery codes for the user."""
        if not self.mfa.recovery_codes:
            return []

        return [
            self.fernet.decrypt(code.encode()).decode()
            for code in self.mfa.recovery_codes
        ]

    def _verify_recovery_code(self, code):
        """
        Verify if a recovery code is valid and remove it if it is.
        :param code: The recovery code provided by the user.
        :return: True if the code is valid, False otherwise.
        """
        try:
            decrypted_codes = self.get_recovery_codes()

            if code in decrypted_codes:
                decrypted_codes.remove(code)

                encrypted_codes = [
                    self.fernet.encrypt(c.encode()).decode() for c in decrypted_codes
                ]

                self.mfa.recovery_codes = encrypted_codes
                self.mfa.save()

                return True

            return False

        except Exception as e:
            logger.error(f"Error verifying recovery code: {str(e)}")
            return False
