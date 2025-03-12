import logging

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from dj_waanverse_auth.models import UserSession
from dj_waanverse_auth.config.settings import auth_config

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Deletes expired user sessions based on creation date and refresh token max age"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        try:
            expiration_threshold = (
                timezone.now() - auth_config.refresh_token_cookie_max_age
            )

            # Query for expired sessions
            expired_sessions = UserSession.objects.filter(
                Q(created_at__lt=expiration_threshold)  # Sessions older than max age
                | Q(is_active=False)  # Include inactive sessions
            )

            count = expired_sessions.count()

            if options["dry_run"]:  # Fixed key access
                self.stdout.write(
                    self.style.WARNING(
                        f"Would delete {count} expired sessions (dry run)"
                    )
                )
                for session in expired_sessions:
                    self.stdout.write(
                        f"Would delete session {session.id} "
                        f"(created: {session.created_at})"
                    )
            else:
                deleted_count = expired_sessions.delete()[0]
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully deleted {deleted_count} expired sessions"
                    )
                )

            logger.info(f"Expired session cleanup completed. Deleted count: {count}")

        except Exception as e:
            logger.error(f"Error during session cleanup: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f"Error during session cleanup: {str(e)}")
            )
            raise
