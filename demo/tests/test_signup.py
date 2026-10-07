from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from rest_framework import status
from dj_waanverse_auth.utils.identifiers import (
    is_email_identifier,
    is_phone_identifier,
    normalize_phone,
    get_identifier_type,
)

Account = get_user_model()

TURNSTILE_ALWAYS_PASS_SECRET = "1x0000000000000000000000000000000AA"
TURNSTILE_ALWAYS_FAIL_SECRET = "2x0000000000000000000000000000000AA"
TURNSTILE_DUMMY_TOKEN = "XXXX.DUMMY.TOKEN.XXXX"

AUTH_CONFIG = "dj_waanverse_auth.views.signup_views.auth_config"

# Fixed validators so the password tests don't depend on the project's settings
TEST_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


class SignupViewTests(TestCase):
    """
    Tests for the signup endpoint.

    Response shapes:
      success -> {"msg": "Account created successfully.", ...}
      error   -> {"msg": {"<field>": "<message>"}}   ("non_field_errors" if no field)
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

    def assert_error(
        self,
        response,
        field,
        expected=None,
        contains=None,
        status_code=status.HTTP_400_BAD_REQUEST,
    ):
        """
        Asserts the error is keyed by its field: response.data["msg"][field].
        Pass `expected` for an exact match, `contains` for a substring.
        """
        self.assertEqual(response.status_code, status_code)
        msg = response.data["msg"]
        self.assertIsInstance(msg, dict)
        self.assertIn(field, msg)
        self.assertIsInstance(msg[field], str)
        if expected is not None:
            self.assertEqual(msg[field], expected)
        if contains is not None:
            self.assertIn(contains, msg[field])

    # ------------------------------------------------------------------
    # Dynamic Custom Serializer Integration Test
    # ------------------------------------------------------------------

    @patch(
        f"{AUTH_CONFIG}.signup_serializer_class", "tests.utils.CustomProfileSerializer"
    )
    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_uses_custom_patched_serializer_with_extra_fields(self):
        """
        Ensures the view resolves the custom path string configuration
        and extracts extended data points cleanly.
        """
        response = self.signup("custom_user@example.com", name="John Doe")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["msg"], "Account created successfully.")

        user = Account.objects.get(email_address="custom_user@example.com")
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

        self.assert_error(response, "identifier", "This field is required.")

    def test_signup_requires_password(self):
        response = self.client.post(
            self.url,
            {"identifier": "wave@example.com"},
            content_type="application/json",
        )

        self.assert_error(response, "password", "This field is required.")

    def test_signup_reports_every_missing_field(self):
        response = self.client.post(self.url, {}, content_type="application/json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("identifier", response.data["msg"])
        self.assertIn("password", response.data["msg"])

    def test_signup_rejects_empty_identifier(self):
        response = self.signup("")

        self.assert_error(response, "identifier", "This field may not be blank.")

    def test_signup_rejects_empty_password(self):
        response = self.client.post(
            self.url,
            {"identifier": "wave@example.com", "password": ""},
            content_type="application/json",
        )

        self.assert_error(response, "password", "This field may not be blank.")

    # ------------------------------------------------------------------
    # Password validation
    # ------------------------------------------------------------------

    @override_settings(AUTH_PASSWORD_VALIDATORS=TEST_PASSWORD_VALIDATORS)
    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_rejects_weak_password_under_password_key(self):
        response = self.signup("wave@example.com", password="abc")

        self.assert_error(response, "password", contains="too short")
        self.assertNotIn("identifier", response.data["msg"])

    @override_settings(AUTH_PASSWORD_VALIDATORS=TEST_PASSWORD_VALIDATORS)
    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_multiple_password_errors_are_joined_into_one_string(self):
        response = self.signup("wave@example.com", password="123")

        self.assert_error(response, "password", contains="too short")
        self.assertIn("entirely numeric", response.data["msg"]["password"])

    # ------------------------------------------------------------------
    # Email signup
    # ------------------------------------------------------------------

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_with_valid_email(self):
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["msg"], "Account created successfully.")
        self.assertEqual(response.data["registration_type"], "email")

        user = Account.objects.get(email_address="wave@example.com")

        self.assertEqual(user.email_address, "wave@example.com")
        self.assertTrue(user.check_password(self.password))
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.phone_verified)

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_normalizes_email(self):
        response = self.signup("  WAVE@EXAMPLE.COM  ")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Account.objects.filter(email_address="wave@example.com").exists()
        )

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
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

                # The exact wording depends on which check catches it first,
                # but the error must be attached to the identifier field.
                self.assert_error(response, "identifier")

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_rejects_existing_email(self):
        Account.objects.create_user(
            email_address="wave@example.com",
            password="ExistingPassword123!",
        )

        response = self.signup("wave@example.com")

        self.assert_error(
            response, "identifier", "Account with this email already exists."
        )

    # ------------------------------------------------------------------
    # Email restrictions
    # ------------------------------------------------------------------

    @patch(f"{AUTH_CONFIG}.allowed_email_domains", ["example.com"])
    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_rejects_email_not_in_allowed_domain(self):
        response = self.signup("wave@gmail.com")

        self.assert_error(response, "identifier", "Invalid email domain.")

    @patch(f"{AUTH_CONFIG}.allowed_email_domains", ["example.com"])
    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_accepts_email_in_allowed_domain(self):
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch(f"{AUTH_CONFIG}.blacklisted_emails", ["blocked@example.com"])
    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_rejects_blacklisted_email(self):
        response = self.signup("blocked@example.com")

        self.assert_error(
            response, "identifier", "This email address is blocked from registration."
        )

    @patch(f"{AUTH_CONFIG}.blacklisted_email_domains", ["blocked.com"])
    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_rejects_blacklisted_domain(self):
        response = self.signup("wave@blocked.com")

        self.assert_error(
            response, "identifier", "This email domain is blocked from registration."
        )

    # ------------------------------------------------------------------
    # Phone signup
    # ------------------------------------------------------------------

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["phone"])
    def test_signup_with_valid_phone(self):
        response = self.signup("+256700123456")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["registration_type"], "phone")

        user = Account.objects.get(phone_number="+256700123456")
        self.assertEqual(user.phone_number, "+256700123456")
        self.assertEqual(user.phone_region, "UG")
        self.assertFalse(user.is_active)
        self.assertFalse(user.phone_verified)
        self.assertFalse(user.email_verified)
        self.assertTrue(user.check_password(self.password))

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["phone"])
    def test_signup_rejects_phone_without_country_code(self):
        response = self.signup("0700123456")

        self.assert_error(response, "identifier")

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["phone"])
    def test_signup_rejects_invalid_phone(self):
        invalid_phones = ["abc", "+", "+256", "+999123456789"]

        for phone in invalid_phones:
            with self.subTest(phone=phone):
                response = self.signup(phone)

                self.assert_error(response, "identifier")

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["phone"])
    def test_signup_rejects_existing_phone(self):
        Account.objects.create_user(
            email_address="existing@example.com",
            phone_number="+256700123456",
            phone_region="UG",
            password="ExistingPassword123!",
        )

        response = self.signup("+256700123456")

        self.assert_error(
            response, "identifier", "Account with this phone already exists."
        )

    # ------------------------------------------------------------------
    # Turnstile verification
    # ------------------------------------------------------------------

    @patch(f"{AUTH_CONFIG}.turnstile_enabled", True)
    @patch(f"{AUTH_CONFIG}.turnstile_secret_key", TURNSTILE_ALWAYS_PASS_SECRET)
    def test_successful_signup_with_turnstile_enabled(self):
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch(f"{AUTH_CONFIG}.turnstile_enabled", True)
    @patch(f"{AUTH_CONFIG}.turnstile_secret_key", TURNSTILE_ALWAYS_FAIL_SECRET)
    def test_failed_signup_with_turnstile_enabled(self):
        response = self.signup("wave@example.com")

        self.assert_error(response, "turnstile_token", "Turnstile verification failed.")

    @patch(f"{AUTH_CONFIG}.turnstile_enabled", False)
    def test_signup_with_turnstile_disabled(self):
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch(f"{AUTH_CONFIG}.turnstile_enabled", True)
    def test_signup_rejects_missing_turnstile_token(self):
        # A misconfiguration is a server error, not a validation error, so the
        # handler leaves it alone and the test client re-raises it.
        with self.assertRaises(ImproperlyConfigured) as context:
            self.signup("wave@example.com")

        self.assertEqual(
            str(context.exception),
            "TURNSTILE_SECRET_KEY must be set when ENABLE_TURNSTILE is True.",
        )

    # ------------------------------------------------------------------
    # Multiple authentication identifiers
    # ------------------------------------------------------------------

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email", "phone"])
    def test_email_is_selected_when_email_and_phone_are_enabled(self):
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = Account.objects.get(email_address="wave@example.com")
        self.assertEqual(user.email_address, "wave@example.com")
        self.assertIsNone(user.phone_number)

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email", "phone"])
    def test_phone_is_selected_when_email_and_phone_are_enabled(self):
        response = self.signup("+256700123456")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = Account.objects.get(phone_number="+256700123456")
        self.assertEqual(user.phone_region, "UG")
        self.assertIsNone(user.email_address)

    # ------------------------------------------------------------------
    # Disabled authentication methods
    # ------------------------------------------------------------------

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["phone"])
    def test_email_signup_rejected_when_email_disabled(self):
        response = self.signup("wave@example.com")

        self.assert_error(response, "identifier", "Please provide a valid identifier.")

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_phone_signup_rejected_when_phone_disabled(self):
        response = self.signup("+256700123456")

        self.assert_error(response, "identifier", "Please provide a valid identifier.")

    # ------------------------------------------------------------------
    # Signup configuration
    # ------------------------------------------------------------------

    @patch(f"{AUTH_CONFIG}.disable_signup", True)
    def test_signup_is_disabled(self):
        response = self.signup("wave@example.com")

        # Not tied to a field, so it comes back under non_field_errors
        self.assert_error(
            response,
            "non_field_errors",
            "Something went wrong. Please try again later.",
            status_code=status.HTTP_403_FORBIDDEN,
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

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email", "phone"])
    def test_identifier_type_email(self):
        self.assertEqual(get_identifier_type("wave@example.com"), "email")

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email", "phone"])
    def test_identifier_type_phone(self):
        self.assertEqual(get_identifier_type("+256700123456"), "phone")

    # ------------------------------------------------------------------
    # No matching / disabled identifier types
    # ------------------------------------------------------------------

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", [])
    def test_signup_rejected_when_no_identifiers_enabled(self):
        response = self.signup("wave@example.com")

        self.assert_error(response, "identifier", "Please provide a valid identifier.")

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_message_when_phone_disabled(self):
        response = self.signup("+256700123456")

        self.assert_error(response, "identifier", "Please provide a valid identifier.")

    # ------------------------------------------------------------------
    # Whitespace-only identifier
    # ------------------------------------------------------------------

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email", "phone"])
    def test_signup_rejects_whitespace_only_identifier(self):
        response = self.signup("     ")

        self.assert_error(response, "identifier", "This field may not be blank.")

    # ------------------------------------------------------------------
    # Case-insensitive duplicate checks
    # ------------------------------------------------------------------

    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_rejects_existing_email_different_case(self):
        Account.objects.create_user(
            email_address="Wave@Example.com",
            password="ExistingPassword123!",
        )

        response = self.signup("wave@example.com")

        self.assert_error(
            response, "identifier", "Account with this email already exists."
        )

    # ------------------------------------------------------------------
    # Case-insensitive blacklist matching
    # ------------------------------------------------------------------

    @patch(f"{AUTH_CONFIG}.blacklisted_emails", ["blocked@example.com"])
    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_rejects_blacklisted_email_different_case(self):
        response = self.signup("BLOCKED@Example.com")

        self.assert_error(
            response, "identifier", "This email address is blocked from registration."
        )

    @patch(f"{AUTH_CONFIG}.blacklisted_email_domains", ["blocked.com"])
    @patch(f"{AUTH_CONFIG}.authentication_identifiers", ["email"])
    def test_signup_rejects_blacklisted_domain_different_case(self):
        response = self.signup("wave@BLOCKED.COM")

        self.assert_error(
            response, "identifier", "This email domain is blocked from registration."
        )

    # ------------------------------------------------------------------
    # Disallowed HTTP methods
    # ------------------------------------------------------------------

    def test_signup_rejects_get(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertIn("non_field_errors", response.data["msg"])

    def test_signup_rejects_put(self):
        response = self.client.put(
            self.url,
            {"identifier": "wave@example.com", "password": self.password},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_signup_rejects_delete(self):
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

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
