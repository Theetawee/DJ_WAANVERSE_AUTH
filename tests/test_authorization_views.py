# from rest_framework import status

# from dj_waanverse_auth.config.settings import auth_config
# from dj_waanverse_auth.services.utils import decode_token, encode_token

# from .test_setup import TestSetup


# class TestAuthorizationViews(TestSetup):
#     def test_get_device_info(self):
#         response = self.client.get(self.device_info_url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#     def test_refresh_access_token_use_cookie(self):
#         self.client.post(self.login_url, data=self.user_1_email_login_data)

#         response = self.client.post(
#             self.refresh_access_token_url,
#         )

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertIn("access_token", response.data)

#     def test_refresh_access_token_use_token(self):
#         login_response = self.client.post(
#             self.login_url, data=self.user_1_email_login_data
#         )
#         refresh_token = login_response.data["refresh_token"]

#         # remove cookie
#         self.client.cookies.pop(
#             auth_config.refresh_token_cookie,
#         )

#         response = self.client.post(
#             self.refresh_access_token_url,
#             data={"refresh_token": refresh_token},
#         )

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertIn("access_token", response.data)

#     def test_refresh_access_token_no_token(self):
#         self.client.post(self.login_url, data=self.user_1_email_login_data)

#         # remove cookie
#         self.client.cookies.pop(
#             auth_config.refresh_token_cookie,
#         )

#         response = self.client.post(
#             self.refresh_access_token_url,
#         )

#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

#     def test_logout(self):
#         self.client.post(self.login_url, data=self.user_1_email_login_data)

#         response = self.client.post(self.logout_url)

#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#         for cookie_name in response.cookies:
#             self.assertEqual(
#                 response.cookies[cookie_name].value,
#                 "",
#                 f"Cookie {cookie_name} was not removed",
#             )

#     def test_get_authenticated_user(self):
#         self.client.post(self.login_url, data=self.user_1_email_login_data)

#         response = self.client.get(self.get_authenticated_user_url)

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["username"], self.test_user_1.username)

#     def test_get_authenticated_user_with_bearer_token(self):
#         login_response = self.client.post(
#             self.login_url, data=self.user_1_email_login_data
#         )

#         access_token = login_response.data["access_token"]

#         self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

#         # remove cookie
#         self.client.cookies.pop(
#             auth_config.access_token_cookie,
#         )

#         self.assertNotIn(auth_config.access_token_cookie, self.client.cookies)

#         response = self.client.get(self.get_authenticated_user_url)

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["username"], self.test_user_1.username)

#     def test_access_with_invalid_sid(self):
#         login_response = self.client.post(
#             self.login_url, data=self.user_1_email_login_data
#         )

#         access_token = login_response.data["access_token"]
#         payload = decode_token(access_token)
#         payload["sid"] = "invalid"
#         access_token = encode_token(payload)

#         self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

#         response = self.client.get(self.get_authenticated_user_url)
#         self.assertIn("identity_error", response.data["detail"])
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

#     def test_access_with_invalid_user_id(self):
#         login_response = self.client.post(
#             self.login_url, data=self.user_1_email_login_data
#         )

#         access_token = login_response.data["access_token"]
#         payload = decode_token(access_token)
#         payload[auth_config.user_id_claim] = "0"
#         access_token = encode_token(payload)

#         self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

#         response = self.client.get(self.get_authenticated_user_url)
#         self.assertIn("user_not_found", response.data["detail"])
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

#     def test_invalid_jwt_claims(self):
#         response = self.client.post(self.login_url, data=self.user_1_email_login_data)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         access_token = response.data.get("access_token")
#         self.assertIsNotNone(access_token)

#         payload = decode_token(access_token)
#         payload.pop("sid", None)  # Remove "sid" claim
#         tampered_token = encode_token(payload)

#         self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered_token}")
#         new_response = self.client.get(self.get_authenticated_user_url)
#         self.assertEqual(new_response.status_code, status.HTTP_401_UNAUTHORIZED)
#         self.assertIn("Invalid token structure", new_response.data["detail"])

#     def test_tampered_token_signature(self):
#         response = self.client.post(self.login_url, data=self.user_1_email_login_data)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         access_token = response.data.get("access_token")
#         self.assertIsNotNone(access_token)

#         tampered_token = access_token[:-1] + ("ark" if access_token[-1] != "milk" else "bag of water")

#         self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered_token}")
#         new_response = self.client.get(self.get_authenticated_user_url)
#         self.assertEqual(new_response.status_code, status.HTTP_401_UNAUTHORIZED)
#         self.assertIn("Invalid token structure", new_response.data["detail"])

#     def test_grant_access_view_with_password_method(self):
#         self.client.post(self.login_url, data=self.user_1_email_login_data)

#         response = self.client.post(
#             self.grant_access_url,
#             {"method": "password", "password": "Test@12"},
#         )

#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#     def test_grant_access_view_with_password_mfa_method(self):
#         self.client.post(self.login_url, data=self.test_user_with_mfa_login_data)
#         self.client.post(
#             self.mfa_login_url,
#             {"code": "123456", "user_id": self.test_user_with_mfa.id},
#         )
#         response = self.client.post(
#             self.grant_access_url,
#             {
#                 "method": "password-mfa",
#                 "password": self.test_user_with_mfa_login_data["password"],
#                 "mfa_code": "123456",
#             },
#         )
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#     def test_grant_access_view_with_mfa_method(self):
#         self.client.post(self.login_url, data=self.test_user_with_mfa_login_data)
#         self.client.post(
#             self.mfa_login_url,
#             {"code": "123456", "user_id": self.test_user_with_mfa.id},
#         )

#         response = self.client.post(
#             self.grant_access_url,
#             {"method": "mfa", "mfa_code": "123456"},
#         )

#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#     def test_grant_access_view_with_invalid_method(self):
#         self.client.post(self.login_url, data=self.user_1_email_login_data)

#         response = self.client.post(
#             self.grant_access_url,
#             {"method": "invalid", "password": "Test@12"},
#         )

#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

#     def test_grant_access_view_with_invalid_password(self):
#         self.client.post(self.login_url, data=self.user_1_email_login_data)

#         response = self.client.post(
#             self.grant_access_url,
#             {"method": "password", "password": "invalid"},
#         )

#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

#     def test_grant_access_view_with_invalid_mfa_code(self):
#         self.client.post(self.login_url, data=self.test_user_with_mfa_login_data)

#         response = self.client.post(
#             self.grant_access_url,
#             {"method": "mfa", "mfa_code": "invalid"},
#         )

#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

#         response = self.client.post(
#             self.grant_access_url,
#             {"method": "password-mfa", "password": "Test@12", "mfa_code": "invalid"},
#         )

#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

#     def test_grant_access_view_with_mfa_user_mfa_disabled(self):
#         self.client.post(self.login_url, data=self.user_1_email_login_data)

#         response = self.client.post(
#             self.grant_access_url,
#             {"method": "password-mfa", "password": "Test@12", "mfa_code": "123456"},
#         )

#         self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
