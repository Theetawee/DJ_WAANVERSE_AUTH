# from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase

# from dj_waanverse_auth.views import SignupView

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

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "Identifier is required.",
        )

    # def test_signup_requires_password(self):
    #     response = self.client.post(
    #         self.url,
    #         {"identifier": "wave@example.com"},
    #         content_type="application/json",
    #     )

    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "Password is required.",
    #     )

    # def test_signup_rejects_empty_identifier(self):
    #     response = self.signup("")

    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "Identifier is required.",
    #     )

    # def test_signup_rejects_empty_password(self):
    #     response = self.client.post(
    #         self.url,
    #         {
    #             "identifier": "wave@example.com",
    #             "password": "",
    #         },
    #         content_type="application/json",
    #     )

    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "Password is required.",
    #     )

    # # ------------------------------------------------------------------
    # # Email signup
    # # ------------------------------------------------------------------

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email"],
    # )
    # def test_signup_with_valid_email(self, mock_identifiers):
    #     response = self.signup("wave@example.com")

    #     self.assertEqual(response.status_code, 201)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "Account created successfully.",
    #     )

    #     user = Account.objects.get(email_address="wave@example.com")

    #     self.assertEqual(
    #         user.email_address,
    #         "wave@example.com",
    #     )

    #     self.assertTrue(user.check_password(self.password))

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email"],
    # )
    # def test_signup_normalizes_email(self, mock_identifiers):
    #     response = self.signup("  WAVE@EXAMPLE.COM  ")

    #     self.assertEqual(response.status_code, 201)

    #     self.assertTrue(
    #         Account.objects.filter(email_address="wave@example.com").exists()
    #     )

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email"],
    # )
    # def test_signup_rejects_invalid_email(self, mock_identifiers):
    #     invalid_emails = [
    #         "invalid",
    #         "invalid@",
    #         "@example.com",
    #         "invalid@example",
    #     ]

    #     for email in invalid_emails:
    #         with self.subTest(email=email):
    #             response = self.signup(email)

    #             self.assertEqual(
    #                 response.status_code,
    #                 400,
    #             )

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email"],
    # )
    # def test_signup_rejects_existing_email(self, mock_identifiers):
    #     Account.objects.create_user(
    #         email_address="wave@example.com",
    #         password="ExistingPassword123!",
    #     )

    #     response = self.signup("wave@example.com")

    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "Account already exists.",
    #     )

    # # ------------------------------------------------------------------
    # # Email restrictions
    # # ------------------------------------------------------------------

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.allowed_email_domains",
    #     ["example.com"],
    # )
    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email"],
    # )
    # def test_signup_rejects_email_not_in_allowed_domain(
    #     self,
    #     mock_identifiers,
    #     mock_domains,
    # ):
    #     response = self.signup("wave@gmail.com")

    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "Invalid email domain.",
    #     )

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.allowed_email_domains",
    #     ["example.com"],
    # )
    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email"],
    # )
    # def test_signup_accepts_email_in_allowed_domain(
    #     self,
    #     mock_identifiers,
    #     mock_domains,
    # ):
    #     response = self.signup("wave@example.com")

    #     self.assertEqual(response.status_code, 201)

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.blacklisted_emails",
    #     ["blocked@example.com"],
    # )
    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email"],
    # )
    # def test_signup_rejects_blacklisted_email(
    #     self,
    #     mock_identifiers,
    #     mock_blacklisted,
    # ):
    #     response = self.signup("blocked@example.com")

    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "This email address is blocked from registration.",
    #     )

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.blacklisted_email_domains",
    #     ["blocked.com"],
    # )
    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email"],
    # )
    # def test_signup_rejects_blacklisted_domain(
    #     self,
    #     mock_identifiers,
    #     mock_domains,
    # ):
    #     response = self.signup("wave@blocked.com")

    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "This email domain is blocked from registration.",
    #     )

    # # ------------------------------------------------------------------
    # # Phone signup
    # # ------------------------------------------------------------------

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["phone"],
    # )
    # def test_signup_with_valid_phone(self, mock_identifiers):
    #     response = self.signup("+256700123456")

    #     self.assertEqual(response.status_code, 201)

    #     user = Account.objects.get(phone_number="+256700123456")

    #     self.assertEqual(
    #         user.phone_number,
    #         "+256700123456",
    #     )

    #     self.assertEqual(
    #         user.phone_region,
    #         "UG",
    #     )

    #     self.assertTrue(user.check_password(self.password))

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["phone"],
    # )
    # def test_signup_rejects_phone_without_country_code(
    #     self,
    #     mock_identifiers,
    # ):
    #     response = self.signup("0700123456")

    #     self.assertEqual(response.status_code, 400)

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["phone"],
    # )
    # def test_signup_rejects_invalid_phone(
    #     self,
    #     mock_identifiers,
    # ):
    #     invalid_phones = [
    #         "abc",
    #         "+",
    #         "+256",
    #         "+999123456789",
    #     ]

    #     for phone in invalid_phones:
    #         with self.subTest(phone=phone):
    #             response = self.signup(phone)

    #             self.assertEqual(
    #                 response.status_code,
    #                 400,
    #             )

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["phone"],
    # )
    # def test_signup_rejects_existing_phone(
    #     self,
    #     mock_identifiers,
    # ):
    #     Account.objects.create_user(
    #         username="existing",
    #         email_address="existing@example.com",
    #         phone_number="+256700123456",
    #         phone_region="UG",
    #         password="ExistingPassword123!",
    #     )

    #     response = self.signup("+256700123456")

    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "Account already exists.",
    #     )

    # # ------------------------------------------------------------------
    # # Username signup
    # # ------------------------------------------------------------------

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["username"],
    # )
    # def test_signup_with_valid_username(
    #     self,
    #     mock_identifiers,
    # ):
    #     response = self.signup("wave")

    #     self.assertEqual(response.status_code, 201)

    #     user = Account.objects.get(username="wave")

    #     self.assertEqual(
    #         user.username,
    #         "wave",
    #     )

    #     self.assertTrue(user.check_password(self.password))

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["username"],
    # )
    # def test_signup_normalizes_username_whitespace(
    #     self,
    #     mock_identifiers,
    # ):
    #     response = self.signup("  wave  ")

    #     self.assertEqual(response.status_code, 201)

    #     self.assertTrue(Account.objects.filter(username="wave").exists())

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["username"],
    # )
    # def test_signup_rejects_existing_username(
    #     self,
    #     mock_identifiers,
    # ):
    #     Account.objects.create_user(
    #         username="wave",
    #         email_address="wave@example.com",
    #         password="ExistingPassword123!",
    #     )

    #     response = self.signup("wave")

    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "Account already exists.",
    #     )

    # # ------------------------------------------------------------------
    # # Multiple authentication identifiers
    # # ------------------------------------------------------------------

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email", "phone"],
    # )
    # def test_email_is_selected_when_email_and_phone_are_enabled(
    #     self,
    #     mock_identifiers,
    # ):
    #     response = self.signup("wave@example.com")

    #     self.assertEqual(response.status_code, 201)

    #     user = Account.objects.get(email_address="wave@example.com")

    #     self.assertEqual(
    #         user.email_address,
    #         "wave@example.com",
    #     )

    #     self.assertIsNone(user.phone_number)

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email", "phone"],
    # )
    # def test_phone_is_selected_when_email_and_phone_are_enabled(
    #     self,
    #     mock_identifiers,
    # ):
    #     response = self.signup("+256700123456")

    #     self.assertEqual(response.status_code, 201)

    #     user = Account.objects.get(phone_number="+256700123456")

    #     self.assertEqual(
    #         user.phone_region,
    #         "UG",
    #     )

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email", "phone", "username"],
    # )
    # def test_username_is_selected_when_all_identifiers_are_enabled(
    #     self,
    #     mock_identifiers,
    # ):
    #     response = self.signup("wave")

    #     self.assertEqual(response.status_code, 201)

    #     self.assertTrue(Account.objects.filter(username="wave").exists())

    # # ------------------------------------------------------------------
    # # Disabled authentication methods
    # # ------------------------------------------------------------------

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["phone"],
    # )
    # def test_email_signup_rejected_when_email_disabled(
    #     self,
    #     mock_identifiers,
    # ):
    #     response = self.signup("wave@example.com")

    #     self.assertEqual(response.status_code, 400)

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email"],
    # )
    # def test_phone_signup_rejected_when_phone_disabled(
    #     self,
    #     mock_identifiers,
    # ):
    #     response = self.signup("+256700123456")

    #     self.assertEqual(response.status_code, 400)

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email"],
    # )
    # def test_username_signup_rejected_when_username_disabled(
    #     self,
    #     mock_identifiers,
    # ):
    #     response = self.signup("wave")

    #     self.assertEqual(response.status_code, 400)

    # # ------------------------------------------------------------------
    # # Signup configuration
    # # ------------------------------------------------------------------

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.disable_signup",
    #     True,
    # )
    # def test_signup_is_disabled(self, mock_disable_signup):
    #     response = self.signup("wave@example.com")

    #     self.assertEqual(response.status_code, 403)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "Signup is disabled.",
    #     )

    # # ------------------------------------------------------------------
    # # Identifier detection
    # # ------------------------------------------------------------------

    # def test_email_identifier_detection(self):
    #     view = SignupView()

    #     self.assertTrue(view._is_email_identifier("wave@example.com"))

    #     self.assertFalse(view._is_email_identifier("wave"))

    # def test_phone_identifier_detection(self):
    #     view = SignupView()

    #     self.assertTrue(view._is_phone_identifier("+256700123456"))

    #     self.assertFalse(view._is_phone_identifier("0700123456"))

    #     self.assertFalse(view._is_phone_identifier("wave"))

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email", "phone", "username"],
    # )
    # def test_identifier_type_email(
    #     self,
    #     mock_identifiers,
    # ):
    #     view = SignupView()

    #     self.assertEqual(
    #         view.get_identifier_type("wave@example.com"),
    #         "email",
    #     )

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email", "phone", "username"],
    # )
    # def test_identifier_type_phone(
    #     self,
    #     mock_identifiers,
    # ):
    #     view = SignupView()

    #     self.assertEqual(
    #         view.get_identifier_type("+256700123456"),
    #         "phone",
    #     )

    # @patch(
    #     "dj_waanverse_auth.views.auth_config.authentication_identifiers",
    #     ["email", "phone", "username"],
    # )
    # def test_identifier_type_username(
    #     self,
    #     mock_identifiers,
    # ):
    #     view = SignupView()

    #     self.assertEqual(
    #         view.get_identifier_type("wave"),
    #         "username",
    #     )
