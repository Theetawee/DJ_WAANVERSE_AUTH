import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

User = get_user_model()


class Command(BaseCommand):
    help = "Creates a superuser with all required fields and optional extra fields"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--email", required=False)
        parser.add_argument("--phone", required=False)
        parser.add_argument(
            "--extras",
            type=str,
            help='Extra fields as JSON string. Example: \'{"first_name": "John", "last_name": "Doe"}\'',
            required=False,
        )

    def handle(self, *args, **options):
        if not options["email"] and not options["phone"]:
            self.stderr.write("Either email or phone must be provided")
            return

        try:
            # Parse extra fields if provided
            extra_fields = {}
            if options.get("extras"):
                try:
                    extra_fields = json.loads(options["extras"])
                    if not isinstance(extra_fields, dict):
                        self.stderr.write("Extras must be a valid JSON object")
                        return
                except json.JSONDecodeError:
                    self.stderr.write("Invalid JSON format for extras")
                    return

            # Create user with base and extra fields
            user = User.objects.create_user(
                username=options["username"],
                password=options["password"],
                email_address=options["email"],
                phone_number=options["phone"],
                **extra_fields,
            )
            user.is_superuser = True
            user.is_staff = True
            user.save()

            # Success message with extra fields info
            success_msg = f'Superuser "{options["username"]}" created successfully'
            if extra_fields:
                success_msg += f" with extra fields: {', '.join(extra_fields.keys())}"

            self.stdout.write(self.style.SUCCESS(success_msg))

        except Exception as e:
            self.stderr.write(str(e))
