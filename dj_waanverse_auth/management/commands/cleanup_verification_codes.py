from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from dj_waanverse_auth.models import VerificationCode


class Command(BaseCommand):
    help = "Delete used and fully expired account verification codes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without deleting anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        queryset = VerificationCode.objects.filter(
            Q(is_used=True)
            | Q(
                code_expires_at__lt=now,
                link_expires_at__lt=now,
            )
        )

        count = queryset.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run: {count} verification code(s) would be deleted."
                )
            )
            return

        deleted, _ = queryset.delete()

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted} verification code record(s).")
        )
