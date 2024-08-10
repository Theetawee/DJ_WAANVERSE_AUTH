from datetime import timedelta
from typing import Any, Dict, Optional, Type

import pyotp
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import PasswordField
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken, Token

from .models import EmailConfirmationCode, MultiFactorAuth, ResetPasswordCode
from .settings import accounts_config
from .utils import (
    check_mfa_status,
    dispatch_email,
    generate_password_reset_code,
    generate_tokens,
    get_client_ip,
    get_email_verification_status,
    handle_email_verification,
    handle_user_login,
    user_email_address,
)
from .validators import password_validator
from .validators import validate_username as username_validator

Account = get_user_model()


class TokenObtainSerializer(serializers.Serializer):
    token_class: Optional[Type[Token]] = None
    default_error_messages = {
        "no_active_account": _("No active account found with the given credentials")
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["login_field"] = serializers.CharField(
            write_only=True, required=True
        )
        self.fields["password"] = PasswordField()

    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        login_field = attrs.get("login_field")
        password = attrs["password"]

        if login_field:
            authenticate_kwargs = {"login_field": login_field, "password": password}
        else:
            raise exceptions.ValidationError(_("Must include valid login credentials."))

        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        self.user = authenticate(**authenticate_kwargs)

        if not api_settings.USER_AUTHENTICATION_RULE(self.user):

            raise serializers.ValidationError(
                {"msg": self.error_messages["no_active_account"]}
            )

        return {}

    @classmethod
    def get_token(cls, user) -> Token:
        token = cls.token_class.for_user(user)
        return token


class LoginSerializer(TokenObtainSerializer):
    token_class = RefreshToken

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        data = super().validate(attrs)
        # Add user data
        data["user"] = self.user

        # Check email verification status
        email_verified = get_email_verification_status(self.user)
        data["email_verified"] = email_verified

        if not email_verified:
            handle_email_verification(self.user)
            data["mfa"] = False  # MFA is reported as off if email is not verified
            return data

        # Check MFA status if email is verified
        data["mfa"] = check_mfa_status(self.user)

        # Generate tokens
        tokens = generate_tokens(self.user)
        data.update(tokens)

        # Handle user login if MFA is not required
        if not data["mfa"]:
            handle_user_login(self.context, self.user)

        return data


class BasicAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["username", "id"]


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "username",
            "email",
        ]


class ReVerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, email):
        try:
            user = Account.objects.get(email=email)
        except Account.DoesNotExist:
            raise serializers.ValidationError(
                "No account is associated with this email address."
            )

        email_address = user_email_address(user)
        if email_address.verified:
            raise serializers.ValidationError("Email is already verified.")

        return email

    def create(self, validated_data):
        email = validated_data["email"]
        try:
            user = Account.objects.get(email=email)
            handle_email_verification(user)
            return email
        except Exception as e:
            raise serializers.ValidationError(
                "An error occurred while sending verification email: " + str(e)
            )


class VerifyEmailSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)

    def validate(self, data):
        code = data.get("code")
        email = data.get("email")

        try:
            user = Account.objects.get(email=email)
            block = EmailConfirmationCode.objects.get(user=user, code=code)

        except EmailConfirmationCode.DoesNotExist:
            raise serializers.ValidationError("Invalid code")
        except Exception:
            raise serializers.ValidationError(
                "Unable to validate code. Please make sure you are validating the correct email address and code."
            )
        # Check if the code has expired
        if (
            timezone.now() - block.created_at
            > accounts_config["EMAIL_VERIFICATION_CODE_LIFETIME"]
        ):
            block.delete()
            raise serializers.ValidationError("Code expired")

        # Delete the used code
        block.delete()
        VerifyEmailSerializer.verify_email(user)
        return data

    @staticmethod
    def verify_email(user):
        email_address = user_email_address(user)
        email_address.verified = True
        email_address.save()


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True, max_length=10)
    password1 = serializers.CharField(required=True, write_only=True)
    password2 = serializers.CharField(required=True, write_only=True)

    def validate_email(self, email):
        """Validate that the email does not already exist."""
        if Account.objects.filter(email=email).exists():
            raise serializers.ValidationError(_("Email already exists."))
        return email

    def validate_username(self, username):
        """Validate the username according to custom rules and ensure it's unique."""
        username = username.lower()
        valid, message = username_validator(username)
        if not valid:
            raise serializers.ValidationError(message)
        if Account.objects.filter(username=username).exists():
            raise serializers.ValidationError(_("Username already exists."))
        return username

    def validate(self, data):
        """Validate that the passwords match."""
        if data.get("password1") != data.get("password2"):
            raise serializers.ValidationError(_("Passwords do not match."))
        try:
            password_validator(data.get("password1"))
        except ValidationError as e:
            raise serializers.ValidationError({"password": e})
        return data

    def create(self, validated_data):
        """Create a new user and return JWT tokens and user data."""
        validated_data["username"] = validated_data["username"].lower()
        password = validated_data.pop("password1")
        validated_data.pop("password2")

        try:
            user = Account.objects.create_user(
                email=validated_data["email"],
                username=validated_data["username"],
                **self.get_additional_fields(validated_data),
                password=password,
            )
            user_email_address(user)

            handle_email_verification(user)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating user: {e}")

        return user

    def get_additional_fields(self, validated_data):
        """Override this method to provide additional fields for user creation."""
        return {}


class MfaCodeSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)

    def validate_code(self, value):
        if len(str(value)) != accounts_config["MFA_CODE_LENGTH"]:
            raise serializers.ValidationError(
                f"The OTP code must be {accounts_config['MFA_CODE_LENGTH']} digits."
            )
        return value


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False)

    def validate(self, attrs):
        refresh = attrs.get("refresh")
        if not refresh:
            request = self.context.get("request")
            if request:
                refresh = request.COOKIES.get(
                    accounts_config["REFRESH_TOKEN_COOKIE_NAME"]
                )
                if not refresh:
                    raise serializers.ValidationError("Refresh token is required.")
        attrs["refresh"] = refresh
        self.token = refresh
        return attrs

    def save(self, **kwargs):
        if api_settings.BLACKLIST_AFTER_ROTATION:

            try:
                if self.token:
                    RefreshToken(self.token).blacklist()
            except Exception as e:
                raise serializers.ValidationError(str(e))


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, email):
        if not Account.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                _("Something went wrong. Please try again or contact support.")
            )
        return email

    def save(self, **kwargs):
        email = self.validated_data["email"]
        code = generate_password_reset_code()
        attempt_count = 1

        try:
            # Get the most recent reset code entry
            last_reset_code = ResetPasswordCode.objects.filter(email=email).latest(
                "created_at"
            )
            if last_reset_code.is_expired:
                last_reset_code.delete()  # Delete expired code
            else:
                if (
                    last_reset_code.attempts
                    >= accounts_config["PASSWORD_RESET_MAX_ATTEMPTS"]
                ):
                    if last_reset_code.cooldown_remaining > timedelta(seconds=0):
                        raise serializers.ValidationError(
                            _(
                                "Too many attempts. Please try again after the cooldown period."
                            )
                        )
                    else:
                        # If cooldown period is over, reset attempts
                        attempt_count = last_reset_code.attempts + 1
                        last_reset_code.delete()  # Delete old code
                else:
                    attempt_count = last_reset_code.attempts + 1
                    last_reset_code.delete()  # Delete old code

        except ResetPasswordCode.DoesNotExist:
            # No previous reset code found, so start with the first attempt
            attempt_count = 1

        # Create and save a new reset code
        reset_code = ResetPasswordCode(email=email, code=code, attempts=attempt_count)
        reset_code.save()

        # Send the email with the new reset code
        email_context = {"code": reset_code.code, "email": email}
        dispatch_email(
            email=email,
            context=email_context,
            template="password_reset",
            subject="Password Reset Code - Waanverse Accounts.",
        )
        return reset_code


class VerifyResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True)
    new_password1 = serializers.CharField(required=True, write_only=True)
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        email = data.get("email")
        code = data.get("code")
        new_password1 = data.get("new_password1")
        new_password2 = data.get("new_password2")

        # Check if passwords match
        if new_password1 != new_password2:
            raise serializers.ValidationError(
                _("The two password fields didn't match.")
            )

        # Check if reset code exists and is valid
        try:
            reset_code = ResetPasswordCode.objects.get(email=email, code=code)
        except ResetPasswordCode.DoesNotExist:
            raise serializers.ValidationError(_("Invalid reset code."))

        # Check if the code has expired
        if reset_code.is_expired:
            reset_code.delete()
            raise serializers.ValidationError(_("The reset code has expired."))

        return data

    def save(self, **kwargs):
        email = self.validated_data["email"]
        new_password = self.validated_data["new_password1"]

        # Update the user's password
        try:
            user = Account.objects.get(email=email)
            user.set_password(new_password)
            user.save()
        except Account.DoesNotExist:
            raise serializers.ValidationError(_("User with this email does not exist."))

        # Delete the used reset code
        ResetPasswordCode.objects.filter(
            email=email, code=self.validated_data["code"]
        ).delete()

        return user


class DeactivateMfaSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    def validate_code(self, value):
        if len(str(value)) != accounts_config["MFA_CODE_LENGTH"]:
            raise serializers.ValidationError(
                f"The OTP code must be {accounts_config['MFA_CODE_LENGTH']} digits."
            )
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        code = attrs.get("code")
        password = attrs.get("password")

        # Validate password
        if not check_password(password, user.password):
            raise serializers.ValidationError("Invalid password.")

        # Validate MFA code
        try:
            mfa = MultiFactorAuth.objects.get(account=user, activated=True)
        except MultiFactorAuth.DoesNotExist:
            raise serializers.ValidationError("MFA is not enabled for this account.")

        # Verify the code using pyotp
        totp = pyotp.TOTP(mfa.secret_key)
        if not totp.verify(code):
            # Fallback to recovery codes if pyotp verification fails
            if code not in mfa.recovery_codes:
                raise serializers.ValidationError("Invalid MFA code.")
            # Remove used recovery code
            mfa.recovery_codes.remove(code)
            mfa.save()
        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        mfa = MultiFactorAuth.objects.get(account=user, activated=True)
        mfa.activated = False
        mfa.secret_key = None
        mfa.recovery_codes = []
        try:
            if accounts_config["MFA_EMAIL_ALERTS"]:
                dispatch_email(
                    email=user.email,
                    template="deactivate_mfa",
                    subject="MFA Deactivated",
                    context={
                        "username": user.username,
                        "email": user.email,
                        "time": timezone.now(),
                        "ip_address": get_client_ip(self.context["request"]),
                        "user_agent": self.context["request"].META.get(
                            "HTTP_USER_AGENT", "<unknown>"
                        )[:255],
                    },
                )
            mfa.save()
            return {"detail": "MFA has been deactivated."}

        except Exception as e:
            raise serializers.ValidationError(str(e))
