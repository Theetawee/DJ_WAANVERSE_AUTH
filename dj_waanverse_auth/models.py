from __future__ import annotations

import hashlib
import hmac
import secrets
from dj_waanverse_auth import settings as auth_config
from django.conf import settings
from django.db import models
from django.utils import timezone

CODE_LENGTH = auth_config.verification_code_length
CODE_TTL = auth_config.verification_code_ttl
LINK_TTL = auth_config.verification_link_ttl
MAX_ATTEMPTS = auth_config.verification_max_attempts


def _generate_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(CODE_LENGTH))


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class VerificationCode(models.Model):
    """
    A single pending verification for an account. Holds both a
    numeric code and a link token from the same issuance — email
    can be verified with either, phone can only use the code.

    Raw code/token values are never stored — only their hashes,
    so a database leak doesn't hand out live verification secrets.
    """

    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_codes",
    )
    code_hash = models.CharField(max_length=64, db_index=True)
    token_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    code_expires_at = models.DateTimeField()
    link_expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    # TODO: add a command to delete all used and expired verification codes, to keep the table from growing indefinitely.

    @classmethod
    def issue_for(cls, account) -> tuple["VerificationCode", str, str]:
        """
        Creates a new verification record and returns it along with
        the raw code and raw link token — the only point at which the
        raw values exist, for the caller to send via email/SMS.

        Invalidates any previously issued, unused codes for this
        account first, so only one verification code/link is ever
        valid at a time — requesting a new one supersedes the old.
        """

        cls.objects.filter(account=account, is_used=False).update(is_used=True)

        code = _generate_code()
        token = _generate_token()
        now = timezone.now()

        instance = cls.objects.create(
            account=account,
            code_hash=_hash(code),
            token_hash=_hash(token),
            code_expires_at=now + CODE_TTL,
            link_expires_at=now + LINK_TTL,
        )

        return instance, code, token

    def matches(self, access: str, *, is_code: bool) -> bool:
        """
        Constant-time comparison against the stored hash for
        whichever access type was supplied.
        """

        expected_hash = self.code_hash if is_code else self.token_hash
        return hmac.compare_digest(_hash(access), expected_hash)

    def is_valid_for(self, *, is_code: bool) -> bool:
        if self.is_used or self.attempts >= MAX_ATTEMPTS:
            return False

        expires_at = self.code_expires_at if is_code else self.link_expires_at
        return timezone.now() < expires_at
