from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status

from dj_waanverse_auth.views.signup_views import SignupView

Account = get_user_model()


class SignupViewTests(TestCase):
    """
    Tests for the signup endpoint.
    """

    def setUp(self):
        self.url = reverse("dj_waanverse_auth_signup")
        self.password = "StrongPassword123!"

    def signup(self, identifier, password=None):
        """
        Helper for making signup requests.
        """
        return self.client.post(
            self.url,
            {
                "identifier": identifier,
                "password": password or self.password,
            },
            content_type="application/json",
        )

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
        self.assertEqual(
            response.data["msg"],
            "Identifier is required.",
        )

    def test_signup_requires_password(self):
        response = self.client.post(
            self.url,
            {"identifier": "wave@example.com"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "Password is required.",
        )

    def test_signup_rejects_empty_identifier(self):
        response = self.signup("")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "Identifier is required.",
        )

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
        self.assertEqual(
            response.data["msg"],
            "Password is required.",
        )

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
            "Account already exists.",
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
    def test_signup_rejects_phone_without_country_code(
        self,
    ):
        response = self.signup("0700123456")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["phone"],
    )
    def test_signup_rejects_invalid_phone(
        self,
    ):
        invalid_phones = [
            "abc",
            "+",
            "+256",
            "+999123456789",
        ]

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
    def test_signup_rejects_existing_phone(
        self,
    ):
        Account.objects.create_user(
            username="existing",
            email_address="existing@example.com",
            phone_number="+256700123456",
            phone_region="UG",
            password="ExistingPassword123!",
        )

        response = self.signup("+256700123456")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "Account already exists.",
        )

    # ------------------------------------------------------------------
    # Username signup
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["username"],
    )
    def test_signup_with_valid_username(
        self,
    ):
        response = self.signup("wAve")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = Account.objects.get(username="wave")

        self.assertEqual(
            user.username,
            "wave",
        )

        self.assertFalse(user.is_active)
        self.assertFalse(user.phone_verified)
        self.assertFalse(user.email_verified)

        self.assertTrue(user.check_password(self.password))

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["username"],
    )
    def test_signup_normalizes_username_whitespace(
        self,
    ):
        response = self.signup("  wave  ")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Account.objects.filter(username="wave").exists())

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["username"],
    )
    def test_signup_rejects_existing_username(
        self,
    ):
        Account.objects.create_user(
            username="wave",
            email_address="wave@example.com",
            password="ExistingPassword123!",
        )

        response = self.signup("wave")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "Account already exists.",
        )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["username"],
    )
    def test_signup_rejects_invalid_username(
        self,
    ):
        invalid_usernames = [
            "ab",
            "a" * 31,
            "invalid username",
            "invalid-username",
            "invalid.username",
            "invalid@username",
        ]

        for username in invalid_usernames:
            with self.subTest(username=username):
                response = self.signup(username)

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    # ------------------------------------------------------------------
    # Multiple authentication identifiers
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone"],
    )
    def test_email_is_selected_when_email_and_phone_are_enabled(
        self,
    ):
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, 201)

        user = Account.objects.get(email_address="wave@example.com")

        self.assertEqual(
            user.email_address,
            "wave@example.com",
        )

        self.assertIsNone(user.phone_number)

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone"],
    )
    def test_phone_is_selected_when_email_and_phone_are_enabled(
        self,
    ):
        response = self.signup("+256700123456")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = Account.objects.get(phone_number="+256700123456")

        self.assertEqual(
            user.phone_region,
            "UG",
        )
        self.assertIsNone(user.email_address)

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone", "username"],
    )
    def test_username_is_selected_when_all_identifiers_are_enabled(self):
        response = self.signup("wave")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Account.objects.filter(username="wave").exists())

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
    def test_phone_signup_rejected_when_phone_disabled(
        self,
    ):
        response = self.signup("+256700123456")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email"],
    )
    def test_username_signup_rejected_when_username_disabled(
        self,
    ):
        response = self.signup("wave")

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
            "Signup is disabled.",
        )

    # ------------------------------------------------------------------
    # Identifier detection
    # ------------------------------------------------------------------

    def test_email_identifier_detection(self):
        view = SignupView()

        self.assertTrue(view._is_email_identifier("wave@example.com"))

        self.assertFalse(view._is_email_identifier("wave"))

    def test_phone_identifier_detection(self):
        view = SignupView()

        self.assertTrue(view._is_phone_identifier("+256700123456"))

        self.assertFalse(view._is_phone_identifier("0700123456"))

        self.assertFalse(view._is_phone_identifier("wave"))

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone", "username"],
    )
    def test_identifier_type_email(
        self,
    ):
        view = SignupView()

        self.assertEqual(
            view.get_identifier_type("wave@example.com"),
            "email",
        )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone", "username"],
    )
    def test_identifier_type_phone(
        self,
    ):
        view = SignupView()

        self.assertEqual(
            view.get_identifier_type("+256700123456"),
            "phone",
        )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone", "username"],
    )
    def test_identifier_type_username(
        self,
    ):
        view = SignupView()

        self.assertEqual(
            view.get_identifier_type("wave"),
            "username",
        )

    # ------------------------------------------------------------------
    # Blacklisted usernames
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.blacklisted_usernames",
        ["admin"],
    )
    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["username"],
    )
    def test_signup_rejects_blacklisted_username(self):
        response = self.signup("admin")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "This username is not available.",
        )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.blacklisted_usernames",
        ["admin"],
    )
    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["username"],
    )
    def test_signup_rejects_blacklisted_username_case_insensitive(self):
        response = self.signup("ADMIN")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "This username is not available.",
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

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["username"],
    )
    def test_email_shaped_identifier_falls_through_to_username_and_is_rejected(self):
        # Email/phone are disabled, so this falls to the username handler,
        # which should reject it for containing invalid characters.
        response = self.signup("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "Username can only contain letters, numbers, and underscores.",
        )

    # ------------------------------------------------------------------
    # Whitespace-only identifier
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["email", "phone", "username"],
    )
    def test_signup_rejects_whitespace_only_identifier(self):
        response = self.signup("    ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Field isolation on username signup
    # ------------------------------------------------------------------

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["username"],
    )
    def test_username_signup_leaves_other_fields_empty(self):
        response = self.signup("wave")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = Account.objects.get(username="wave")

        self.assertIsNone(user.email_address)
        self.assertIsNone(user.phone_number)

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
            "Account already exists.",
        )

    @patch(
        "dj_waanverse_auth.views.signup_views.auth_config.authentication_identifiers",
        ["username"],
    )
    def test_signup_rejects_existing_username_different_case(self):
        Account.objects.create_user(
            username="Wave",
            email_address="wave@example.com",
            password="ExistingPassword123!",
        )

        response = self.signup("wave")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["msg"],
            "Account already exists.",
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

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

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
        phone_number, phone_region = SignupView.normalize_phone("+256700123456")

        self.assertEqual(phone_number, "+256700123456")
        self.assertEqual(phone_region, "UG")

    def test_normalize_phone_missing_country_code(self):
        with self.assertRaises(ValueError):
            SignupView.normalize_phone("0700123456")

    def test_normalize_phone_malformed_number(self):
        with self.assertRaises(ValueError):
            SignupView.normalize_phone("+abc")

    def test_normalize_phone_invalid_number(self):
        with self.assertRaises(ValueError):
            SignupView.normalize_phone("+999123456789")

        with self.assertRaises(ValueError):
            SignupView.normalize_phone("+1234")  # too short to be a real US/CA number
