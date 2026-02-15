"""Tests for the memory encryption module."""

import os

import pytest

from src.memory.encryption import MemoryEncryption, derive_memory_key


class TestMemoryEncryption:
    """Test AES-256-GCM encryption."""

    def test_encrypt_decrypt(self):
        """Test basic encrypt/decrypt cycle."""
        key = os.urandom(32)
        enc = MemoryEncryption(master_key=key)

        plaintext = b"Hello, World!"
        ciphertext = enc.encrypt(plaintext)
        decrypted = enc.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_decrypt_string(self):
        """Test string encryption."""
        key = os.urandom(32)
        enc = MemoryEncryption(master_key=key)

        text = "Sensitive user data"
        ciphertext = enc.encrypt_string(text)
        decrypted = enc.decrypt_string(ciphertext)

        assert decrypted == text

    def test_different_ciphertext_each_time(self):
        """Each encryption should produce different output (random nonce)."""
        key = os.urandom(32)
        enc = MemoryEncryption(master_key=key)

        plaintext = b"Same data"
        ct1 = enc.encrypt(plaintext)
        ct2 = enc.encrypt(plaintext)

        assert ct1 != ct2  # Different nonces

    def test_wrong_key_fails(self):
        """Decryption with wrong key should fail."""
        key1 = os.urandom(32)
        key2 = os.urandom(32)

        enc1 = MemoryEncryption(master_key=key1)
        enc2 = MemoryEncryption(master_key=key2)

        ciphertext = enc1.encrypt(b"secret")

        with pytest.raises(Exception):
            enc2.decrypt(ciphertext)

    def test_tampered_ciphertext_fails(self):
        """Tampered ciphertext should fail decryption (GCM auth tag)."""
        key = os.urandom(32)
        enc = MemoryEncryption(master_key=key)

        ciphertext = enc.encrypt(b"data")
        # Tamper with ciphertext
        tampered = bytearray(ciphertext)
        tampered[-1] ^= 0xFF
        tampered = bytes(tampered)

        with pytest.raises(Exception):
            enc.decrypt(tampered)

    def test_invalid_key_size(self):
        """Invalid key size should raise ValueError."""
        with pytest.raises(ValueError, match="32 bytes"):
            MemoryEncryption(master_key=b"short")

    def test_associated_data(self):
        """Test encryption with associated data (AAD)."""
        key = os.urandom(32)
        enc = MemoryEncryption(master_key=key)

        aad = b"conversation-id-123"
        plaintext = b"message content"

        ciphertext = enc.encrypt(plaintext, associated_data=aad)

        # Correct AAD
        decrypted = enc.decrypt(ciphertext, associated_data=aad)
        assert decrypted == plaintext

        # Wrong AAD should fail
        with pytest.raises(Exception):
            enc.decrypt(ciphertext, associated_data=b"wrong-aad")

    def test_derive_memory_key(self):
        """Test key derivation from password."""
        salt = os.urandom(32)
        key = derive_memory_key("my-password", salt)

        assert len(key) == 32
        assert isinstance(key, bytes)

        # Same password + salt = same key
        key2 = derive_memory_key("my-password", salt)
        assert key == key2

        # Different password = different key
        key3 = derive_memory_key("different-password", salt)
        assert key != key3
