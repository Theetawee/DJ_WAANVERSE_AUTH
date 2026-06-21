from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from dj_waanverse_auth import settings as auth_config
from logging import getLogger
from dj_waanverse_auth.utils.email_utils import request_code_flow
from dj_waanverse_auth.utils.login import verify_code_flow

from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

logger = getLogger(__name__)


def validate_email_address(email: str, platform: str = "web"):
    """
    Validates rules and creates a user.
    Raises ValidationError on failure.
    Returns the User object on success.
    """
    try:
        validate_email(email)
    except ValidationError:
        return Response(
            {"detail": "Invalid email address format."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    email = email.strip().lower()
    domain = email.split("@")[-1]

    allowed_domains = auth_config.allowed_email_domains or []
    blacklisted_emails = auth_config.blacklisted_emails or []
    blacklisted_domains = auth_config.blacklisted_email_domains or []

    allowed_domains = [d.lower() for d in allowed_domains]
    blacklisted_emails = [e.lower() for e in blacklisted_emails]
    blacklisted_domains = [d.lower() for d in blacklisted_domains]

    # Check Allowed Domains
    if allowed_domains and domain not in allowed_domains:
        return Response(
            {"detail": "Invalid email domain."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check Blacklist
    if email in blacklisted_emails:
        return Response(
            {"detail": "This email address is blocked from registration."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check Blacklisted Domains
    if blacklisted_domains and domain in blacklisted_domains:
        return Response(
            {"detail": "This email domain is blocked from registration."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Step 5: Check if user already exists
    Account = get_user_model()
    # Assuming the field name in your model is 'email_address' based on your snippet
    if Account.objects.filter(email_address__iexact=email).exists():
        return Response(
            {"detail": "Account already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return request_code_flow(email=email, platform=platform, is_signup=True)


@api_view(["POST"])
@permission_classes([AllowAny])
def signup_view(request):
    if auth_config.disable_signup:
        return Response(
            {"detail": "Pong"},
            status=status.HTTP_200_OK,
        )
    email_address = request.data.get("email_address")
    code = request.data.get("code")
    platform = request.query_params.get("platform", "web")  # web or app

    if not email_address:
        return Response(
            {"detail": "Email address is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not code:
        response = validate_email_address(email_address, platform=platform)
        return response

    print(email_address, code)

    if email_address and code:
        response = verify_code_flow(request, email_address, code)
        return response
