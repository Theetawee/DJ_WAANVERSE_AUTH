from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from django.urls import reverse

from dj_waanverse_auth.models import VerificationCode

Account = get_user_model()

VIEW_MODULE = "dj_waanverse_auth.views.verify_views"


class RequestVerificationViewTests(TestCase):
    """
    Tests for the "send me a code/link" endpoint. Assumes
    AUTHENTICATION_IDENTIFIERS includes both email and phone unless
    a specific test overrides it.
    """

    def setUp(self):
        self.url = reverse("dj_waanverse_auth_request_verification")

    def request_verification(self, identifier, delivery=None):
        payload = {"identifier": identifier}
        if delivery is not None:
            payload["delivery"] = delivery
        return self.client.post(self.url, payload, content_type="application/json")

    def make_pending_account(self, **kwargs):
        defaults = {
            "email_address": "wave@example.com",
            "password": "StrongPassword123!",
        }
        defaults.update(kwargs)
        return Account.objects.create_user(**defaults)  # is_active=False by default

    # ------------------------------------------------------------------
    # Basic validation
    # ------------------------------------------------------------------

    def test_requires_identifier(self):
        response = self.client.post(self.url, {}, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_blank_identifier(self):
        response = self.request_verification("   ")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_invalid_delivery_value(self):
        response = self.request_verification(
            "wave@example.com", delivery="carrier-pigeon"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_unrecognized_identifier(self):
        response = self.request_verification("not-an-email-or-phone")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_link_delivery_for_phone(self):
        response = self.request_verification("+256700123456", delivery="link")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Non-existent / already-active accounts — generic response, no leak
    # ------------------------------------------------------------------

    @patch(f"{VIEW_MODULE}.send_verification_code_email")
    def test_nonexistent_account_returns_generic_success(self, mock_send):
        response = self.request_verification("nobody@example.com")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_not_called()
        self.assertEqual(VerificationCode.objects.count(), 0)

    @patch(f"{VIEW_MODULE}.send_verification_code_email")
    def test_already_active_account_returns_generic_success_and_sends_nothing(
        self, mock_send
    ):
        Account.objects.create_user(
            email_address="active@example.com",
            password="StrongPassword123!",
            is_active=True,
        )

        response = self.request_verification("active@example.com")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_not_called()
        self.assertEqual(VerificationCode.objects.count(), 0)

    def test_response_message_identical_for_missing_and_active_accounts(self):
        Account.objects.create_user(
            email_address="active@example.com",
            password="StrongPassword123!",
            is_active=True,
        )

        missing_response = self.request_verification("nobody@example.com")
        active_response = self.request_verification("active@example.com")

        self.assertEqual(missing_response.data["msg"], active_response.data["msg"])

    # ------------------------------------------------------------------
    # Email — code delivery
    # ------------------------------------------------------------------

    @patch(f"{VIEW_MODULE}.send_verification_code_email")
    def test_email_code_delivery_issues_code_and_calls_sender(self, mock_send):
        account = self.make_pending_account(email_address="wave@example.com")

        response = self.request_verification("wave@example.com", delivery="code")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(VerificationCode.objects.filter(account=account).count(), 1)

        mock_send.assert_called_once()
        called_account, called_code = mock_send.call_args.args
        self.assertEqual(called_account.pk, account.pk)
        self.assertTrue(called_code.isdigit())
        self.assertEqual(len(called_code), 6)

    @patch(f"{VIEW_MODULE}.send_verification_code_email")
    def test_email_defaults_to_code_delivery_when_omitted(self, mock_send):
        self.make_pending_account(email_address="wave@example.com")

        response = self.request_verification("wave@example.com")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called_once()

    # ------------------------------------------------------------------
    # Email — link delivery
    # ------------------------------------------------------------------

    @patch(f"{VIEW_MODULE}.send_verification_link_email")
    @patch(f"{VIEW_MODULE}.send_verification_code_email")
    def test_email_link_delivery_calls_link_sender_not_code_sender(
        self, mock_code_send, mock_link_send
    ):
        account = self.make_pending_account(email_address="wave@example.com")

        response = self.request_verification("wave@example.com", delivery="link")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_link_send.assert_called_once()
        mock_code_send.assert_not_called()

        called_account, called_token = mock_link_send.call_args.args
        self.assertEqual(called_account.pk, account.pk)
        self.assertTrue(
            len(called_token) > 20
        )  # opaque, but shouldn't be trivially short

    # ------------------------------------------------------------------
    # Phone — code delivery
    # ------------------------------------------------------------------

    @patch(f"{VIEW_MODULE}.send_verification_sms")
    def test_phone_code_delivery_calls_sms_sender(self, mock_send):
        self.make_pending_account(
            email_address=None,
            phone_number="+256700123456",
            phone_region="UG",
        )

        response = self.request_verification("+256700123456")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called_once()

        called_phone, called_code = mock_send.call_args.args
        self.assertEqual(called_phone, "+256700123456")
        self.assertTrue(called_code.isdigit())
        self.assertEqual(len(called_code), 6)

    def test_phone_with_malformed_number_rejected_before_lookup(self):
        response = self.request_verification("not-a-real-number")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Delivery failure is swallowed, response stays generic
    # ------------------------------------------------------------------

    @patch(f"{VIEW_MODULE}.send_verification_code_email", side_effect=Exception("boom"))
    def test_sender_exception_does_not_surface_as_500(self, mock_send):
        self.make_pending_account(email_address="wave@example.com")

        response = self.request_verification("wave@example.com", delivery="code")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called_once()

    # ------------------------------------------------------------------
    # Each request issues a fresh code, doesn't reuse stale ones
    # ------------------------------------------------------------------

    @patch(f"{VIEW_MODULE}.send_verification_code_email")
    def test_reissuing_invalidates_previous_code(self, mock_send):
        account = self.make_pending_account(email_address="wave@example.com")

        self.request_verification("wave@example.com")
        first_code = VerificationCode.objects.get(account=account, is_used=False)

        self.request_verification("wave@example.com")

        first_code.refresh_from_db()
        self.assertTrue(first_code.is_used)

        self.assertEqual(VerificationCode.objects.filter(account=account).count(), 2)
        self.assertEqual(
            VerificationCode.objects.filter(account=account, is_used=False).count(), 1
        )
        self.assertEqual(mock_send.call_count, 2)
