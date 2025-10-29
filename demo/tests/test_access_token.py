import jwt
from django.urls import reverse
from dj_waanverse_auth import settings
from rest_framework import status
from datetime import datetime, timezone
from django.contrib.auth import get_user_model
from dj_waanverse_auth.models import AccessCode
from django.test import TestCase
from dj_waanverse_auth.utils.token_utils import decode_token
from dj_waanverse_auth.models import UserSession

Account = get_user_model()


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.login_url = reverse("dj_waanverse_auth_auth")
        self.account = Account.objects.create_user(
            email_address="test@example.com", username="testuser", name="Test User"
        )

    def test_access_token_structure(self):
        """Verify the structure and claims of the access token returned upon login."""
        email = "test@example.com"

        # Step 1: Request authentication code
        self.client.post(self.login_url, {"email_address": email})

        access_code = AccessCode.objects.get(email_address=email)
        code = access_code.code

        # Step 2: Submit code for login
        response = self.client.post(
            self.login_url,
            {"email_address": email, "code": code},
        )

        # Step 3: Validate response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(settings.access_token_cookie, response.data)

        # Step 4: Decode the JWT access token
        token = response.data[settings.access_token_cookie]

        session_id = UserSession.objects.get(account=self.account).id

        try:
            decoded_token = decode_token(
                token,
            )
        except jwt.ExpiredSignatureError:
            self.fail("Access token is expired immediately upon creation.")
        except jwt.InvalidTokenError as e:
            self.fail(f"Invalid access token: {e}")

        # Step 5: Assert essential JWT claims exist
        required_claims = ["id", "exp", "iat", "sid", "token_type"]
        for claim in required_claims:
            self.assertIn(claim, decoded_token, f"Missing claim: {claim}")

        # Step 6: Verify claim types
        self.assertIsInstance(decoded_token["id"], int)
        self.assertIsInstance(decoded_token["exp"], int)
        self.assertIsInstance(decoded_token["iat"], int)
        self.assertIsInstance(decoded_token["token_type"], str)
        self.assertEqual(decoded_token["token_type"], "access")
        self.assertIsInstance(decoded_token["sid"], int)

        # Step 7: Check timestamps
        exp = datetime.fromtimestamp(decoded_token["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(decoded_token["iat"], tz=timezone.utc)

        # Expiration should be after issued-at and within reasonable range (e.g., < 1 day)
        self.assertGreater(exp, iat)
        expiration_time = settings.access_token_cookie_max_age
        self.assertLessEqual(exp - iat, expiration_time)

        # Step 8: Ensure email matches the logged-in user
        self.assertEqual(decoded_token["id"], self.account.id)
        self.assertEqual(decoded_token["sid"], session_id)

        # Step 10: Check refresh token presence
        self.assertIn(settings.refresh_token_cookie, response.data)
        self.assertTrue(
            response.data[settings.refresh_token_cookie].startswith("ey")
        )  # typical JWT prefix

        # Step 11: Confirm user object is included
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email_address"], email)
