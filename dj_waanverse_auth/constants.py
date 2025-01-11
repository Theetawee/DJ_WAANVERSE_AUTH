from django.db.models import TextChoices


class AccountStatus(TextChoices):
    SUSPENDED = "suspended", "Suspended"
    BANNED = "banned", "Banned"
    ORDINARY = "ordinary", "Ordinary"
    VERIFIED = "verified", "Verified"
