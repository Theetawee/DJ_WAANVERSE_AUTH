from __future__ import annotations
from dj_waanverse_auth import settings
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from dj_waanverse_auth.models import Session


class Command(BaseCommand):
    help = "Delete revoked and inactive authentication sessions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--inactive-days",
            type=int,
            default=None,
            help="Delete sessions that have not been used for this many days. Default: 30.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without deleting anything.",
        )

    def handle(self, *args, **options):
        inactive_days = options["inactive_days"]
        dry_run = options["dry_run"]

        if inactive_days is not None and inactive_days < 1:
            self.stderr.write(self.style.ERROR("--inactive-days must be at least 1."))
            return

        now = timezone.now()
        if inactive_days is None:
            cutoff = now - settings.refresh_token_lifetime
        else:
            cutoff = now - timedelta(days=inactive_days)

        revoked_qs = Session.objects.filter(is_revoked=True)
        inactive_qs = Session.objects.filter(
            is_revoked=False,
            last_used_at__lt=cutoff,
        )

        revoked_count = revoked_qs.count()
        inactive_count = inactive_qs.count()
        total = revoked_count + inactive_count

        if dry_run:
            self.stdout.write(f"Revoked sessions: {revoked_count}")
            self.stdout.write(f"Inactive sessions: {inactive_count}")
            self.stdout.write(
                self.style.WARNING(f"Dry run: {total} session(s) would be deleted.")
            )
            return

        deleted, _ = Session.objects.filter(
            Q(is_revoked=True)
            | Q(
                is_revoked=False,
                last_used_at__lt=cutoff,
            )
        ).delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} session record(s)."))
