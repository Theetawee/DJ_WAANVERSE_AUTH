from rest_framework import serializers, exceptions
from django.contrib.auth import authenticate, user_logged_in
from rest_framework_simplejwt.tokens import RefreshToken
from .models import EmailConfirmationCode, ResetPasswordCode, MultiFactorAuth
from .utils import (
    generate_password_reset_code,
    dispatch_email,
    user_email_address,
    handle_email_verification,
)
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import update_last_login

from typing import Optional, Type, Dict, Any
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.serializers import PasswordField
from django.contrib.auth import get_user_model
from .settings import accounts_config
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

            raise serializers.ValidationError(self.error_messages["no_active_account"])

        return {}

    @classmethod
    def get_token(cls, user) -> Token:
        token = cls.token_class.for_user(user)
        return token


class LoginSerializer(TokenObtainSerializer):
    token_class = RefreshToken

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        data = super().validate(attrs)
        email_address = user_email_address(self.user)

        try:
            account_mfa = MultiFactorAuth.objects.get(account=self.user)
            data["mfa"] = account_mfa.activated
        except MultiFactorAuth.DoesNotExist:
            data["mfa"] = False

        refresh = self.get_token(self.user)
        data["refresh_token"] = str(refresh)
        data["access_token"] = str(refresh.access_token)
        data["user"] = self.user

        if not data["mfa"] and email_address and email_address.verified:
            user_logged_in.send(
                sender=self.user.__class__,
                request=self.context["request"],
                user=self.user,
            )
            update_last_login(None, self.user)

        if email_address and email_address.verified:
            data["email_verified"] = True
        else:
            data["email_verified"] = False
            handle_email_verification(self.user)
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
            handle_email_verification(user)
            user_email_address(user)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating user: {e}")

        return user

    def get_additional_fields(self, validated_data):
        """Override this method to provide additional fields for user creation."""
        return {}


class MfaCodeSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)

    def validate_code(self, value):
        # Ensure the code is a 6-digit integer
        if len(str(value)) != 6:
            raise serializers.ValidationError("The OTP code must be 6 digits.")
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
                _("Something went wrong. Please try again.")
            )
        return email

    def save(self, **kwargs):
        """
        Password reset code is generated freely and quickly for the first 3 attempts after which the user will have to wait for one hour to try again.
        """
        email = self.validated_data["email"]
        code = generate_password_reset_code()

        try:
            existing_code = ResetPasswordCode.objects.get(email=email)
            attempts = existing_code.attempts
            created_at = existing_code.created_at

            if attempts >= 3:
                cooldown_end_time = created_at + timedelta(hours=1)
                if timezone.now() < cooldown_end_time:
                    raise serializers.ValidationError(
                        _("Too many attempts. Please try again after an hour.")
                    )
            existing_code.delete()
            new_password_reset = ResetPasswordCode.objects.create(
                email=email, code=code, attempts=attempts + 1
            )

        except ResetPasswordCode.DoesNotExist:
            new_password_reset = ResetPasswordCode.objects.create(
                email=email, code=code
            )
        email_context = {"code": new_password_reset.code, "email": email}
        dispatch_email(
            email=email,
            context=email_context,
            template="password_reset",
            subject="Password Reset Code - Waanverse Accounts.",
        )
        return new_password_reset


class VerifyResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True)
    new_password1 = serializers.CharField(required=True)
    new_password2 = serializers.CharField(required=True)

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
        user = Account.objects.get(email=email)
        user.set_password(new_password)
        user.save()
        # Delete the used reset code
        ResetPasswordCode.objects.filter(
            email=email, code=self.validated_data["code"]
        ).delete()

        return user
