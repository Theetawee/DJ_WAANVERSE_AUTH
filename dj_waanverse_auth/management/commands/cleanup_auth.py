from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clean up expired and invalid authentication records."

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

        print(dry_run, "Here")

        self.stdout.write("Cleaning authentication records...\n")

        self.stdout.write(self.style.MIGRATE_HEADING("Sessions"))
        call_command(
            "cleanup_sessions",
            inactive_days=inactive_days,
            dry_run=dry_run,
            stdout=self.stdout,
        )

        self.stdout.write(self.style.MIGRATE_HEADING("Verification codes"))
        call_command(
            "cleanup_verification_codes",
            dry_run=dry_run,
            stdout=self.stdout,
        )

        self.stdout.write(self.style.MIGRATE_HEADING("Password reset codes"))
        call_command(
            "cleanup_password_reset_codes",
            dry_run=dry_run,
            stdout=self.stdout,
        )

        self.stdout.write(self.style.SUCCESS("\nAuthentication cleanup complete."))
