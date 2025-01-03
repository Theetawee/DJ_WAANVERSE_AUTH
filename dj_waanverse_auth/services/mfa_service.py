import secrets

import pyotp
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

    def get_mfa(self):
        """Get or create the MFA record for the user."""
        mfa, created = MultiFactorAuth.objects.get_or_create(account=self.user)
        return mfa

    def is_mfa_enabled(self):
        """Check if MFA is enabled for the user."""
        return self.mfa.activated

    def generate_secret(self):
        """Generate and save a new MFA secret for the user."""
        secret_key = pyotp.random_base32()
        self.mfa.secret_key = secret_key
        self.mfa.activated = True
        self.mfa.activated_at = now()
        self.mfa.save()
        return secret_key

    def get_provisioning_uri(self):
        """
        Get the provisioning URI for the user's MFA setup.
        This is used to generate a QR code for authenticator apps.
        """
        if not self.mfa.secret_key:
            raise ValueError("No MFA secret found. Please generate a secret first.")

        issuer_name = auth_config.mfa_issuer
        return pyotp.totp.TOTP(self.mfa.secret_key).provisioning_uri(
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
        if not self.mfa.secret_key:
            raise ValueError("No MFA secret found. Cannot verify token.")

        totp = pyotp.TOTP(self.mfa.secret_key)
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
