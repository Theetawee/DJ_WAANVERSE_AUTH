import hashlib
import secrets
from base64 import urlsafe_b64encode

import pyotp
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils.timezone import now

from dj_waanverse_auth.models import MultiFactorAuth
from dj_waanverse_auth.settings import auth_config


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
        raw_secret = pyotp.random_base32()
        encoded_secret = self.fernet.encrypt(raw_secret.encode()).decode()

        self.mfa.secret_key = encoded_secret
        self.mfa.activated = True
        self.mfa.activated_at = now()
        self.mfa.save()

        return raw_secret

    def get_decoded_secret(self):
        """Decode the stored secret key."""
        if not self.mfa.secret_key:
            raise ValueError("No MFA secret found.")
        return self.fernet.decrypt(self.mfa.secret_key.encode()).decode()

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

    def verify_token(self, token):
        """
        Verify an MFA token provided by the user.
        :param token: The TOTP token to verify.
        :return: True if the token is valid, False otherwise.
        """
        raw_secret = self.get_decoded_secret()
        totp = pyotp.TOTP(raw_secret)
        return totp.verify(token)

    def disable_mfa(self):
        """Disable MFA for the user."""
        self.mfa.secret_key = None
        self.mfa.activated = False
        self.mfa.activated_at = None
        self.mfa.save()

    def generate_recovery_codes(self):
        """Generate recovery codes for the user."""
        count = auth_config.mfa_recovery_codes_count
        return [str(secrets.randbelow(10**7)).zfill(7) for _ in range(count)]

    def set_recovery_codes(self):
        """Set recovery codes for the user."""
        self.mfa.recovery_codes = self.generate_recovery_codes()
        self.mfa.save()

    def get_recovery_codes(self):
        """Get recovery codes for the user."""
        return self.mfa.recovery_codes

    def verify_recovery_code(self, code):
        """
        Verify if a recovery code is valid and remove it if it is.
        :param code: The recovery code provided by the user.
        :return: True if the code is valid, False otherwise.
        """
        if not self.user.mfa or not self.user.mfa.recovery_codes:
            return False

        if code in self.user.mfa.recovery_codes:
            self.user.mfa.recovery_codes.remove(code)
            self.user.mfa.save()
            return True

        return False
