"""Tests for the secrets vault."""

import pytest

from src.security.secrets_vault import SecretsVault, VaultError


class TestSecretsVault:
    """Test the encrypted secrets vault."""

    def test_initialize_and_unlock(self, vault_path):
        """Test vault initialization and unlock cycle."""
        vault = SecretsVault(vault_path=vault_path)

        # Initialize
        vault.initialize("test-password-123")
        assert not vault.is_locked
        assert vault.is_initialized

        # Lock
        vault.lock()
        assert vault.is_locked

        # Unlock
        vault.unlock("test-password-123")
        assert not vault.is_locked
        vault.lock()

    def test_store_and_retrieve(self, vault_path):
        """Test storing and retrieving secrets."""
        vault = SecretsVault(vault_path=vault_path)
        vault.initialize("password")

        vault.set("API_KEY", "sk-test-12345")
        vault.set("TOKEN", "tok-abc")

        assert vault.get("API_KEY") == "sk-test-12345"
        assert vault.get("TOKEN") == "tok-abc"
        assert vault.get("NONEXISTENT") is None

        vault.lock()

    def test_persistence(self, vault_path):
        """Test that secrets persist across lock/unlock cycles."""
        vault = SecretsVault(vault_path=vault_path)
        vault.initialize("password")
        vault.set("KEY", "value-123")
        vault.lock()

        # Re-open
        vault2 = SecretsVault(vault_path=vault_path)
        vault2.unlock("password")
        assert vault2.get("KEY") == "value-123"
        vault2.lock()

    def test_wrong_password(self, vault_path):
        """Test that wrong password fails."""
        vault = SecretsVault(vault_path=vault_path)
        vault.initialize("correct-password")
        vault.lock()

        vault2 = SecretsVault(vault_path=vault_path)
        with pytest.raises(VaultError, match="Failed to decrypt"):
            vault2.unlock("wrong-password")

    def test_delete_secret(self, vault_path):
        """Test deleting a secret."""
        vault = SecretsVault(vault_path=vault_path)
        vault.initialize("password")
        vault.set("KEY", "value")

        assert vault.delete("KEY")
        assert vault.get("KEY") is None
        assert not vault.delete("NONEXISTENT")
        vault.lock()

    def test_list_keys(self, vault_path):
        """Test listing key names (never values)."""
        vault = SecretsVault(vault_path=vault_path)
        vault.initialize("password")
        vault.set("A", "1")
        vault.set("B", "2")

        keys = vault.list_keys()
        assert set(keys) == {"A", "B"}
        vault.lock()

    def test_has_key(self, vault_path):
        """Test checking if a key exists."""
        vault = SecretsVault(vault_path=vault_path)
        vault.initialize("password")
        vault.set("EXISTS", "yes")

        assert vault.has("EXISTS")
        assert not vault.has("MISSING")
        vault.lock()

    def test_locked_operations_fail(self, vault_path):
        """Test that operations on a locked vault fail."""
        vault = SecretsVault(vault_path=vault_path)
        vault.initialize("password")
        vault.lock()

        with pytest.raises(VaultError, match="locked"):
            vault.get("KEY")

        with pytest.raises(VaultError, match="locked"):
            vault.set("KEY", "value")

    def test_double_initialize_fails(self, vault_path):
        """Test that initializing an existing vault fails."""
        vault = SecretsVault(vault_path=vault_path)
        vault.initialize("password")
        vault.lock()

        vault2 = SecretsVault(vault_path=vault_path)
        with pytest.raises(VaultError, match="already exists"):
            vault2.initialize("other-password")

    def test_get_required(self, vault_path):
        """Test get_required raises for missing keys."""
        vault = SecretsVault(vault_path=vault_path)
        vault.initialize("password")

        with pytest.raises(VaultError, match="not found"):
            vault.get_required("MISSING")

        vault.set("EXISTS", "val")
        assert vault.get_required("EXISTS") == "val"
        vault.lock()
