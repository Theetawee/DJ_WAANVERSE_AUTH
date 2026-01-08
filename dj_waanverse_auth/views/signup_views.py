from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from dj_waanverse_auth import settings as auth_config
from django.contrib.auth import get_user_model
from logging import getLogger

logger = getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def signup_view(request):
    email_address = request.data.get("email_address")

    if not email_address:
        return Response(
            {"detail": "Email address is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # We call the logic function. If it fails, it raises ValidationError.
        # If it succeeds, it returns the user (which we can ignore or use).
        _create_account_logic(email_address)

        return Response(
            {"detail": "Account created successfully."},
            status=status.HTTP_201_CREATED,
        )

    except ValidationError as e:
        # Handle logical validation errors (invalid format, blacklisted, duplicate)
        # e.message usually contains the string, or str(e) converts the list of errors
        error_message = e.message if hasattr(e, "message") else str(e.args[0])
        return Response(
            {"detail": error_message},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as e:
        # Handle unexpected server errors
        logger.error(f"Error creating account for {email_address}: {e}")
        return Response(
            {"detail": "An unexpected error occurred while creating the account."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _create_account_logic(email: str):
    """
    Validates rules and creates a user.
    Raises ValidationError on failure.
    Returns the User object on success.
    """
    # Step 1: Validate email format
    try:
        validate_email(email)
    except ValidationError:
        raise ValidationError("Invalid email address format.")

    # Normalize email and extract domain
    email = email.strip().lower()
    domain = email.split("@")[-1]

    # Step 2: Load configuration lists (Handle NoneTypes safely)
    allowed_domains = getattr(auth_config, "allowed_email_domains", []) or []
    blacklisted_emails = getattr(auth_config, "blacklisted_emails", []) or []

    # Normalize lists for comparison
    allowed_domains = [d.lower() for d in allowed_domains]
    blacklisted_emails = [e.lower() for e in blacklisted_emails]

    # Step 3: Check Allowed Domains
    if allowed_domains and domain not in allowed_domains:
        raise ValidationError(f"Email domain '{domain}' is not allowed.")

    # Step 4: Check Blacklist
    if email in blacklisted_emails:
        raise ValidationError("This email address is blocked from registration.")

    # Step 5: Check if user already exists
    Account = get_user_model()
    # Assuming the field name in your model is 'email_address' based on your snippet
    if Account.objects.filter(email_address__iexact=email).exists():
        raise ValidationError("Account already exists.")

    # Step 6: Create new user
    # We let potential DB errors bubble up to the generic Exception handler in the view
    return Account.objects.create_user(email_address=email)
