"""
Broker connector tests.

Tests key vault encryption and Alpaca client mocking.
"""

from django.test import TestCase, override_settings
from apps.broker_connector.key_vault import encrypt_key, decrypt_key, mask_key


# Generate a valid Fernet key for testing
TEST_FERNET_KEY = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="


@override_settings(ENCRYPTION_KEY=TEST_FERNET_KEY)
class KeyVaultTest(TestCase):
    """Tests for API key encryption/decryption."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypting then decrypting returns the original key."""
        original = "AKIAIOSFODNN7EXAMPLE"
        encrypted = encrypt_key(original)
        decrypted = decrypt_key(encrypted)
        self.assertEqual(original, decrypted)

    def test_encrypted_differs_from_plaintext(self):
        """Encrypted value is not the same as plaintext."""
        original = "my-secret-key-123"
        encrypted = encrypt_key(original)
        self.assertNotEqual(original, encrypted)

    def test_empty_string_passthrough(self):
        """Empty string encrypts/decrypts to empty string."""
        self.assertEqual(encrypt_key(""), "")
        self.assertEqual(decrypt_key(""), "")

    def test_mask_key_shows_last_four(self):
        """mask_key shows only the last 4 characters."""
        self.assertEqual(mask_key("AKIAIOSFODNN7EXAMPLE"), "****MPLE")

    def test_mask_short_key(self):
        """Short keys are fully masked."""
        self.assertEqual(mask_key("abc"), "****")
        self.assertEqual(mask_key(""), "****")


@override_settings(ENCRYPTION_KEY="wrong-key-format")
class KeyVaultBadKeyTest(TestCase):
    """Tests for error handling with invalid encryption key."""

    def test_bad_key_raises_error(self):
        """Invalid Fernet key raises an error on encrypt."""
        with self.assertRaises(Exception):
            encrypt_key("test-key")
