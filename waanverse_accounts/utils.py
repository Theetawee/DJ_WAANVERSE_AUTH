from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
import random
import re
import string


def set_cookies(
    response, access_token=None, refresh_token=None, login_failed=None, mfa=None
):
    """
    Set a cookie on the response.

    Parameters:
    - response (HttpResponse): The response object to set the cookie on.
    - access_token (str): The access token.
    - refresh_token (str): The refresh token.
    """
    access_token_lifetime = settings.SIMPLE_JWT.get(
        "ACCESS_TOKEN_LIFETIME"
    ).total_seconds()
    refresh_token_lifetime = settings.SIMPLE_JWT.get(
        "REFRESH_TOKEN_LIFETIME"
    ).total_seconds()

    if access_token:
        response.set_cookie(
            settings.BROWSER_CONFIG.get("ACCESS_COOKIE_NAME", "access_token"),
            access_token,
            max_age=int(access_token_lifetime),
            path=settings.BROWSER_CONFIG.get("COOKIE_PATH", "/"),
            domain=settings.BROWSER_CONFIG.get("COOKIE_DOMAIN", None),
            secure=settings.BROWSER_CONFIG.get("COOKIE_SECURE", True),
            httponly=settings.BROWSER_CONFIG.get("HTTP_ONLY", True),
            samesite=settings.BROWSER_CONFIG.get("COOKIE_SAMESITE", "Lax"),
        )

    if refresh_token:
        response.set_cookie(
            settings.BROWSER_CONFIG.get("REFRESH_COOKIE_NAME", "refresh_token"),
            refresh_token,
            max_age=int(refresh_token_lifetime),
            path=settings.BROWSER_CONFIG.get("COOKIE_PATH", "/"),
            domain=settings.BROWSER_CONFIG.get("COOKIE_DOMAIN", None),
            secure=settings.BROWSER_CONFIG.get("COOKIE_SECURE", True),
            httponly=settings.BROWSER_CONFIG.get("HTTP_ONLY", True),
            samesite=settings.BROWSER_CONFIG.get("COOKIE_SAMESITE", "Lax"),
        )

    if mfa:
        response.set_cookie(
            settings.BROWSER_CONFIG.get("MFA_COOKIE_NAME", "mfa"),
            mfa,
            max_age=settings.BROWSER_CONFIG.get("MFA_COOKIE_LIFETIME").total_seconds(),
            path=settings.BROWSER_CONFIG.get("COOKIE_PATH", "/"),
            domain=settings.BROWSER_CONFIG.get("COOKIE_DOMAIN", None),
            secure=settings.BROWSER_CONFIG.get("COOKIE_SECURE", True),
            httponly=settings.BROWSER_CONFIG.get("HTTP_ONLY", True),
            samesite=settings.BROWSER_CONFIG.get("COOKIE_SAMESITE", "Lax"),
        )

    return response


def is_valid_username(username):
    # Check for minimum length
    if len(username) < 4:
        return False, "Username should be at least 4 characters long."

    # Check for allowed characters (letters, numbers, and underscores)
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username should only contain letters, numbers, and underscores."

    # Check for maximum length (optional)
    if len(username) > 30:
        return False, "Username should not exceed 30 characters."

    return True, ""


def generate_confirmation_code():
    """
    Generates a 6-digit confirmation code.

    Returns:
    - str: The generated confirmation code.
    """
    return str(random.randint(100000, 999999))


def dispatch_email(context, email, subject, template):
    """
    Sends an email to the sepcified email

    Args:
        context (any): The context of the email which will be passed to the template
        email (str): The email address to which the email will be sent
        subject (str): The subject of the email
        template (str): The name of the template located in the 'emails' folder
    """
    template_name = f"emails/{template}.html"
    convert_to_html_content = render_to_string(
        template_name=template_name, context=context
    )
    plain_message = strip_tags(convert_to_html_content)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[
            email,
        ],
        html_message=convert_to_html_content,
        fail_silently=True,
    )


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def generate_password_reset_code():
    digits = random.choice(string.digits)
    uppercase = random.choice(string.ascii_uppercase)
    lowercase = random.choice(string.ascii_lowercase)

    # Generate the remaining 3 characters randomly from all allowed characters
    remaining_characters = string.ascii_letters + string.digits
    remaining = "".join(random.choice(remaining_characters) for _ in range(3))

    # Combine all characters and shuffle
    code_list = list(digits + uppercase + lowercase + remaining)
    random.shuffle(code_list)

    return "".join(code_list)
