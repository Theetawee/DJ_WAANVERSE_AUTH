from django.test import TestCase

from dj_waanverse_auth.utils import identifiers as identifier_utils


class IsEmailIdentifierTests(TestCase):
    def test_valid_email(self):
        self.assertTrue(identifier_utils.is_email_identifier("wave@example.com"))

    def test_invalid_email(self):
        self.assertFalse(identifier_utils.is_email_identifier("not-an-email"))


class IsPhoneIdentifierTests(TestCase):
    def test_valid_phone(self):
        self.assertTrue(identifier_utils.is_phone_identifier("+256700123456"))

    def test_missing_plus_prefix(self):
        self.assertFalse(identifier_utils.is_phone_identifier("256700123456"))

    def test_invalid_number(self):
        self.assertFalse(identifier_utils.is_phone_identifier("+1234"))


class NormalizePhoneTests(TestCase):
    def test_valid_number_returns_e164_and_region(self):
        number, region = identifier_utils.normalize_phone("+256700123456")
        self.assertEqual(number, "+256700123456")
        self.assertEqual(region, "UG")

    def test_missing_country_code_raises(self):
        with self.assertRaises(ValueError):
            identifier_utils.normalize_phone("0700123456")

    def test_malformed_number_raises(self):
        with self.assertRaises(ValueError):
            identifier_utils.normalize_phone("+abc")


class GetIdentifierTypeTests(TestCase):
    def test_detects_email(self):
        self.assertEqual(
            identifier_utils.get_identifier_type("wave@example.com"),
            "email",
        )

    def test_detects_phone(self):
        self.assertEqual(
            identifier_utils.get_identifier_type("+256700123456"),
            "phone",
        )

    def test_returns_none_for_unrecognized_identifier(self):
        self.assertIsNone(identifier_utils.get_identifier_type("just-a-username"))
