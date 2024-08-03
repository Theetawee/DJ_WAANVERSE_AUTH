from rest_framework import serializers, exceptions
from django.contrib.auth import authenticate, user_logged_in
from rest_framework_simplejwt.tokens import RefreshToken
from .models import EmailConfirmationCode, ResetPasswordCode
from .utils import (
    generate_confirmation_code,
    generate_password_reset_code,
    dispatch_email,
)
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.models import update_last_login

from typing import Optional, Type, Dict, Any
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.serializers import PasswordField
from django.contrib.auth import get_user_model


Account = get_user_model()


class TokenObtainSerializer(serializers.Serializer):
    token_class: Optional[Type[Token]] = None

    default_error_messages = {
        "no_active_account": _("No active account found with the given credentials")
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["username"] = serializers.CharField(write_only=True, required=True)
        self.fields["password"] = PasswordField()

    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        username = attrs.get("username")
        password = attrs["password"]

        if username:
            authenticate_kwargs = {"username": username, "password": password}
        else:
            raise exceptions.ValidationError(_("Must include a username"))

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
        refresh = self.get_token(self.user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)
        data["user"] = self.user
        data["mfa"] = self.user.mfa_activated
        user_logged_in.send(
            sender=self.user.__class__,
            request=self.context["request"],
            user=self.user,
        )

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)
        return data


class BasicAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["username", "id"]


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "mfa_activated",
            "name",
            "username",
            "email",
            "phone",
            "profile_image",
            "date_of_birth",
            "pronouns",
            "custom_pronouns",
            "date_joined",
            "last_login",
            "is_active",
            "is_staff",
        ]
        read_only_fields = ["date_joined", "last_login"]


class SignupEmailVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, email):
        if Account.objects.filter(email=email).exists():
            raise serializers.ValidationError("Email already exists")
        return email

    def create(self, validated_data):
        email = validated_data["email"]
        code = generate_confirmation_code()
        if EmailConfirmationCode.objects.filter(email=email).exists():
            EmailConfirmationCode.objects.filter(email=email).delete()
        try:
            new_block = EmailConfirmationCode.objects.create(email=email, code=code)
            dispatch_email(
                subject="Email verification code",
                context={"code": code},
                template="verify_email",
                email=email,
            )
            return new_block
        except Exception as e:
            raise serializers.ValidationError(str(e))


class VerifyEmailSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, max_length=6)
    email = serializers.EmailField(required=True)

    def validate(self, data):
        code = data.get("code")
        email = data.get("email")

        try:
            block = EmailConfirmationCode.objects.get(email=email, code=code)
        except EmailConfirmationCode.DoesNotExist:
            raise serializers.ValidationError("Invalid code")

        # Check if the code has expired
        if timezone.now() - block.created_at > timedelta(minutes=10):
            block.delete()
            raise serializers.ValidationError("Code expired")

        # Delete the used code
        block.delete()

        return data


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True, max_length=10)
    name = serializers.CharField(required=True, max_length=255)
    password1 = serializers.CharField(required=True, write_only=True)
    password2 = serializers.CharField(required=True, write_only=True)
    date_of_birth = serializers.DateField(required=True)
    pronouns = serializers.ChoiceField(choices=Account.PRONOUNS, required=True)
    custom_pronouns = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )

    def validate_email(self, email):
        if Account.objects.filter(email=email).exists():
            raise serializers.ValidationError(_("Email already exists."))
        return email

    def validate_username(self, username):
        username = username.lower()

        # Username regex validator
        regex_validator = RegexValidator(
            regex=r"^[A-Za-z][A-Za-z0-9_]{3,29}$",
            message=_(
                "Username can only contain letters, numbers, and underscores, and must be between 4 and 30 characters long."
            ),
        )
        try:
            regex_validator(username)
        except DjangoValidationError:
            raise serializers.ValidationError(
                _(
                    "Username can only contain letters, numbers, and underscores, and must be between 4 and 30 characters long."
                )
            )

        # Check for existing username
        if Account.objects.filter(username=username).exists():
            raise serializers.ValidationError(_("Username already exists."))

        # Check blacklisted usernames
        blacklisted_usernames = getattr(settings, "BLACKLISTED_USERNAMES", [])
        if username in blacklisted_usernames:
            raise serializers.ValidationError(_("This username is not allowed."))

        return username

    def validate(self, data):
        if data.get("password1") != data.get("password2"):
            raise serializers.ValidationError(_("Passwords do not match."))
        return data

    def create(self, validated_data):
        validated_data["username"] = validated_data["username"].lower()
        password = validated_data.pop("password1")
        user = Account.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            name=validated_data["name"],
            date_of_birth=validated_data["date_of_birth"],
            pronouns=validated_data["pronouns"],
            custom_pronouns=validated_data.get("custom_pronouns", None),
            password=password,
        )
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": AccountSerializer(user).data,
        }


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
                    settings.BROWSER_CONFIG["REFRESH_COOKIE_NAME"]
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


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "name",
            "email",
            "phone",
            "profile_image",
            "date_of_birth",
            "pronouns",
            "custom_pronouns",
        ]
