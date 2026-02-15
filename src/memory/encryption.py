"""
AES-256-GCM encryption for Gulama's memory store.

All memory data is encrypted at rest. This module provides
transparent encryption/decryption for the SQLite memory database.
"""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

NONCE_SIZE = 12
KEY_SIZE = 32  # AES-256


class MemoryEncryption:
    """
    AES-256-GCM encryption for memory data at rest.

    Usage:
        enc = MemoryEncryption(master_key=derived_key)
        ciphertext = enc.encrypt(b"sensitive data")
        plaintext = enc.decrypt(ciphertext)
    """

    def __init__(self, master_key: bytes):
        if len(master_key) != KEY_SIZE:
            raise ValueError(f"Master key must be {KEY_SIZE} bytes")
        self._aesgcm = AESGCM(master_key)

    def encrypt(self, plaintext: bytes, associated_data: bytes | None = None) -> bytes:
        """
        Encrypt data with AES-256-GCM.
        Returns: nonce (12 bytes) + ciphertext + tag (16 bytes)
        """
        nonce = os.urandom(NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce + ciphertext

    def decrypt(self, data: bytes, associated_data: bytes | None = None) -> bytes:
        """
        Decrypt AES-256-GCM encrypted data.
        Input: nonce (12 bytes) + ciphertext + tag (16 bytes)
        """
        if len(data) < NONCE_SIZE + 16:
            raise ValueError("Data too short to contain valid ciphertext")
        nonce = data[:NONCE_SIZE]
        ciphertext = data[NONCE_SIZE:]
        return self._aesgcm.decrypt(nonce, ciphertext, associated_data)

    def encrypt_string(self, text: str, associated_data: bytes | None = None) -> bytes:
        """Encrypt a string."""
        return self.encrypt(text.encode("utf-8"), associated_data)

    def decrypt_string(self, data: bytes, associated_data: bytes | None = None) -> str:
        """Decrypt to a string."""
        return self.decrypt(data, associated_data).decode("utf-8")


def derive_memory_key(master_password: str, salt: bytes) -> bytes:
    """Derive a memory encryption key from the master password."""
    kdf = Scrypt(
        salt=salt,
        length=KEY_SIZE,
        n=2**17,
        r=8,
        p=1,
    )
    return kdf.derive(master_password.encode("utf-8"))
