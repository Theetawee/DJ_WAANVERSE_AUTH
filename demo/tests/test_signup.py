from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from dj_waanverse_auth.utils.identifiers import (
    is_email_identifier,
    is_phone_identifier,
    normalize_phone,
    get_identifier_type,
)

from django.core.exceptions import ImproperlyConfigured

Account = get_user_model()

TURNSTILE_ALWAYS_PASS_SECRET = "1x0000000000000000000000000000000AA"
TURNSTILE_ALWAYS_FAIL_SECRET = "2x0000000000000000000000000000000AA"
TURNSTILE_DUMMY_TOKEN = "XXXX.DUMMY.TOKEN.XXXX"


class SignupViewTests(TestCase):
    """
    Tests for the signup endpoint.
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("dj_waanverse_auth_signup")
        self.password = "StrongPassword123!"

    def signup(self, identifier, password=None, turnstile_token=None, **extra_fields):
        """
        Helper for making signup requests. Supports keyword arguments for custom attributes.
        """
        payload = {
            "identifier": identifier,
            "password": password if password is not None else self.password,
            "turnstile_token": turnstile_token or TURNSTILE_DUMMY_TOKEN,
            **extra_fields,
        }
        return self.client.post(
            self.url,
            payload,
            content_type="application/json",
        )

    # ------------------------------------------------------------------
    # Dynamic Custom Serializer Integration Test
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.signup_serializer_class",
        "tests.utils.CustomProfileSerializer",
    )
    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_uses_custom_patched_serializer_with_extra_fields(self):
        """
        Ensures the view resolves the custom path string configuration
        and extracts extended data points cleanly.
        """
        # We simulate passing down a custom 'name' field inside our standard JSON payload
        response = self.signup("custom_user@example.com", name="John Doe")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["msg"], "Account created successfully.")

        user = Account.objects.get(email_address="custom_user@example.com")
        # If your User model has a 'name' field, verify it was saved successfully
        if hasattr(user, "name"):
            self.assertEqual(user.name, "John Doe")

    # ------------------------------------------------------------------
    # Basic validation
    # ------------------------------------------------------------------

    def test_signup_requires_identifier(self):
        response = self.client.post(
            self.url,
            {"password": self.password},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Serializer default message field check
        self.assertIn("required", response.data["msg"])

    def test_signup_requires_password(self):
        response = self.client.post(
            self.url,
            {"identifier": "wave@example.com"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("required", response.data["msg"])

    def test_signup_rejects_empty_identifier(self):
        response = self.signup("")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This field may not be blank.", response.data["msg"])

    def test_signup_rejects_empty_password(self):
        response = self.client.post(
            self.url,
            {
                "identifier": "wave@example.com",
                "password": "",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This field may not be blank.", response.data["msg"])

    # ------------------------------------------------------------------
    # Email signup
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_with_valid_email(self):
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["msg"],
            "Account created successfully.",
        )

        user = Account.objects.get(email_address="wave@example.com")

        self.assertEqual(
            user.email_address,
            "wave@example.com",
        )

        self.assertTrue(user.check_password(self.password))
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.phone_verified)

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_normalizes_email(self):
        response = self.signup("  WAVE@EXAMPLE.COM  ")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(
            Account.objects.filter(email_address="wave@example.com").exists()
        )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_rejects_invalid_email(self):
        invalid_emails = [
            "invalid",
            "invalid@",
            "@example.com",
            "invalid@example",
        ]

        for email in invalid_emails:
            with self.subTest(email=email):
                response = self.signup(email)

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_rejects_existing_email(self):
        Account.objects.create_user(
            email_address="wave@example.com",
            password="ExistingPassword123!",
        )

        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "Account with this email already exists.",
        )

    # ------------------------------------------------------------------
    # Email restrictions
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.allowed_email_domains",
        ["example.com"],
    )
    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_rejects_email_not_in_allowed_domain(
        self,
    ):
        response = self.signup("wave@gmail.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "Invalid email domain.",
        )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.allowed_email_domains",
        ["example.com"],
    )
    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_accepts_email_in_allowed_domain(
        self,
    ):
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.blacklisted_emails",
        ["blocked@example.com"],
    )
    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_rejects_blacklisted_email(
        self,
    ):
        response = self.signup("blocked@example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "This email address is blocked from registration.",
        )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.blacklisted_email_domains",
        ["blocked.com"],
    )
    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_rejects_blacklisted_domain(
        self,
    ):
        response = self.signup("wave@blocked.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "This email domain is blocked from registration.",
        )

    # ------------------------------------------------------------------
    # Phone signup
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["phone"],
    )
    def test_signup_with_valid_phone(self):
        response = self.signup("+256700123456")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = Account.objects.get(phone_number="+256700123456")
        self.assertEqual(
            user.phone_number,
            "+256700123456",
        )
        self.assertEqual(
            user.phone_region,
            "UG",
        )
        self.assertFalse(user.is_active)
        self.assertFalse(user.phone_verified)
        self.assertFalse(user.email_verified)
        self.assertTrue(user.check_password(self.password))

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["phone"],
    )
    def test_signup_rejects_phone_without_country_code(self):
        response = self.signup("0700123456")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["phone"],
    )
    def test_signup_rejects_invalid_phone(self):
        invalid_phones = ["abc", "+", "+256", "+999123456789"]

        for phone in invalid_phones:
            with self.subTest(phone=phone):
                response = self.signup(phone)
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["phone"],
    )
    def test_signup_rejects_existing_phone(self):
        Account.objects.create_user(
            email_address="existing@example.com",
            phone_number="+256700123456",
            phone_region="UG",
            password="ExistingPassword123!",
        )

        response = self.signup("+256700123456")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"], "Account with this phone already exists."
        )

    # ------------------------------------------------------------------
    # Turnstile verification
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.turnstile_enabled",
        True,
    )
    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.turnstile_secret_key",
        TURNSTILE_ALWAYS_PASS_SECRET,
    )
    def test_successful_signup_with_turnstile_enabled(self):
        response = self.signup("wave@example.com")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.turnstile_enabled",
        True,
    )
    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.turnstile_secret_key",
        TURNSTILE_ALWAYS_FAIL_SECRET,
    )
    def test_failed_signup_with_turnstile_enabled(self):
        response = self.signup("wave@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("dj_waanverse_auth.views.signup_views.auth_config.turnstile_enabled", False)
    def test_signup_with_turnstile_disabled(self):
        response = self.signup("wave@example.com")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("dj_waanverse_auth.views.signup_views.auth_config.turnstile_enabled", True)
    def test_signup_rejects_missing_turnstile_token(self):
        with self.assertRaises(ImproperlyConfigured) as context:
            self.signup("wave@example.com")

        self.assertEqual(
            str(context.exception),
            "TURNSTILE_SECRET_KEY must be set when ENABLE_TURNSTILE is True.",
        )

    # ------------------------------------------------------------------
    # Multiple authentication identifiers
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone"],
    )
    def test_email_is_selected_when_email_and_phone_are_enabled(self):
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = Account.objects.get(email_address="wave@example.com")

        self.assertEqual(user.email_address, "wave@example.com")
        self.assertIsNone(user.phone_number)

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone"],
    )
    def test_phone_is_selected_when_email_and_phone_are_enabled(self):
        response = self.signup("+256700123456")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = Account.objects.get(phone_number="+256700123456")

        self.assertEqual(user.phone_region, "UG")
        self.assertIsNone(user.email_address)

    # ------------------------------------------------------------------
    # Disabled authentication methods
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["phone"],
    )
    def test_email_signup_rejected_when_email_disabled(self):
        response = self.signup("wave@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_phone_signup_rejected_when_phone_disabled(self):
        response = self.signup("+256700123456")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Signup configuration
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.disable_signup",
        True,
    )
    def test_signup_is_disabled(self):
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["msg"],
            "Something went wrong. Please try again later.",
        )

    # ------------------------------------------------------------------
    # Identifier detection
    # ------------------------------------------------------------------

    def test_email_identifier_detection(self):
        self.assertTrue(is_email_identifier("wave@example.com"))
        self.assertFalse(is_email_identifier("wave"))

    def test_phone_identifier_detection(self):
        self.assertTrue(is_phone_identifier("+256700123456"))
        self.assertFalse(is_phone_identifier("0700123456"))
        self.assertFalse(is_phone_identifier("wave"))

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone"],
    )
    def test_identifier_type_email(self):
        self.assertEqual(
            get_identifier_type("wave@example.com"),
            "email",
        )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone"],
    )
    def test_identifier_type_phone(self):
        self.assertEqual(
            get_identifier_type("+256700123456"),
            "phone",
        )

    # ------------------------------------------------------------------
    # No matching / disabled identifier types
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        [],
    )
    def test_signup_rejected_when_no_identifiers_enabled(self):
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "Please provide a valid identifier.",
        )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_message_when_phone_disabled(self):
        response = self.signup("+256700123456")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "Please provide a valid identifier.",
        )

    # ------------------------------------------------------------------
    # Whitespace-only identifier
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone"],
    )
    def test_signup_rejects_whitespace_only_identifier(self):
        response = self.signup("     ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Case-insensitive duplicate checks
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_rejects_existing_email_different_case(self):
        Account.objects.create_user(
            email_address="Wave@Example.com",
            password="ExistingPassword123!",
        )

        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "Account with this email already exists.",
        )

    # ------------------------------------------------------------------
    # Case-insensitive blacklist matching
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.blacklisted_emails",
        ["blocked@example.com"],
    )
    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_rejects_blacklisted_email_different_case(self):
        response = self.signup("BLOCKED@Example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "This email address is blocked from registration.",
        )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.blacklisted_email_domains",
        ["blocked.com"],
    )
    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_signup_rejects_blacklisted_domain_different_case(self):
        response = self.signup("wave@BLOCKED.COM")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "This email domain is blocked from registration.",
        )

    # ------------------------------------------------------------------
    # Disallowed HTTP methods
    # ------------------------------------------------------------------

    def test_signup_rejects_get(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_signup_rejects_put(self):
        response = self.client.put(
            self.url,
            {
                "identifier": "wave@example.com",
                "password": self.password,
            },
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_signup_rejects_delete(self):
        response = self.client.delete(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    # ------------------------------------------------------------------
    # normalize_phone unit tests
    # ------------------------------------------------------------------

    def test_normalize_phone_valid_number(self):
        phone_number, phone_region = normalize_phone("+256700123456")

        self.assertEqual(phone_number, "+256700123456")
        self.assertEqual(phone_region, "UG")

    def test_normalize_phone_missing_country_code(self):
        with self.assertRaises(ValueError):
            normalize_phone("0700123456")

    def test_normalize_phone_malformed_number(self):
        with self.assertRaises(ValueError):
            normalize_phone("+abc")

    def test_normalize_phone_invalid_number(self):
        with self.assertRaises(ValueError):
            normalize_phone("+999123456789")

        with self.assertRaises(ValueError):
            normalize_phone("+1234")
