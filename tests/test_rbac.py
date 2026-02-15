"""Tests for the RBAC (Role-Based Access Control) system."""

from __future__ import annotations

import pytest

from src.security.rbac import RBACManager, RBACError, BUILT_IN_ROLES, PERMISSIONS


class TestRBACManager:
    """Tests for RBACManager."""

    def setup_method(self):
        self.rbac = RBACManager()

    def test_builtin_roles_loaded(self):
        """All 5 built-in roles should be loaded."""
        roles = self.rbac.list_roles()
        role_names = {r["name"] for r in roles}
        assert role_names == {"admin", "operator", "user", "viewer", "guest"}

    def test_admin_has_all_permissions(self):
        """Admin role should have all permissions."""
        user = self.rbac.create_user("admin1", "strongpassword", role_name="admin")
        for perm in PERMISSIONS:
            assert self.rbac.check_permission(user.id, perm)

    def test_guest_minimal_permissions(self):
        """Guest role should only have chat.send."""
        user = self.rbac.create_user("guest1", "password123", role_name="guest")
        assert self.rbac.check_permission(user.id, "chat.send")
        assert not self.rbac.check_permission(user.id, "tools.execute")
        assert not self.rbac.check_permission(user.id, "admin.users")

    def test_create_user(self):
        """Creating a user should work."""
        user = self.rbac.create_user("testuser", "mypassword", email="test@example.com")
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role_name == "user"
        assert user.is_active

    def test_create_duplicate_user_fails(self):
        """Creating a user with duplicate username should fail."""
        self.rbac.create_user("dup", "pass1")
        with pytest.raises(RBACError, match="already exists"):
            self.rbac.create_user("dup", "pass2")

    def test_create_user_invalid_role_fails(self):
        """Creating a user with invalid role should fail."""
        with pytest.raises(RBACError, match="not found"):
            self.rbac.create_user("user1", "pass", role_name="superadmin")

    def test_authenticate_success(self):
        """Authentication with correct credentials should work."""
        self.rbac.create_user("auth_user", "correctpassword")
        user = self.rbac.authenticate("auth_user", "correctpassword")
        assert user is not None
        assert user.username == "auth_user"
        assert user.last_login != ""

    def test_authenticate_wrong_password(self):
        """Authentication with wrong password should fail."""
        self.rbac.create_user("auth_user2", "correctpassword")
        result = self.rbac.authenticate("auth_user2", "wrongpassword")
        assert result is None

    def test_authenticate_nonexistent_user(self):
        """Authentication for non-existent user should fail."""
        result = self.rbac.authenticate("nobody", "password")
        assert result is None

    def test_authenticate_inactive_user(self):
        """Authentication for deactivated user should fail."""
        user = self.rbac.create_user("inactive", "password")
        self.rbac.deactivate_user(user.id)
        result = self.rbac.authenticate("inactive", "password")
        assert result is None

    def test_get_user_by_username(self):
        """Getting user by username should work."""
        self.rbac.create_user("findme", "pass")
        found = self.rbac.get_user_by_username("findme")
        assert found is not None
        assert found.username == "findme"

    def test_channel_linking(self):
        """Linking and finding users by channel ID should work."""
        user = self.rbac.create_user("telegram_user", "pass")
        self.rbac.link_channel(user.id, "telegram", "12345678")

        found = self.rbac.get_user_by_channel("telegram", "12345678")
        assert found is not None
        assert found.username == "telegram_user"

    def test_update_user_role(self):
        """Updating a user's role should work."""
        user = self.rbac.create_user("promo", "pass", role_name="viewer")
        assert self.rbac.check_permission(user.id, "tools.execute") is False

        self.rbac.update_user_role(user.id, "operator")
        assert self.rbac.check_permission(user.id, "tools.execute") is True

    def test_create_custom_role(self):
        """Creating a custom role should work."""
        role = self.rbac.create_role(
            "analyst",
            "Data analyst — read + export",
            ["chat.send", "data.own", "data.export"],
        )
        assert role.name == "analyst"
        assert "data.export" in role.permissions
        assert not role.is_system

    def test_delete_system_role_fails(self):
        """Deleting a system role should fail."""
        with pytest.raises(RBACError, match="Cannot delete system role"):
            self.rbac.delete_role("admin")

    def test_delete_role_with_users_fails(self):
        """Deleting a role that has users assigned should fail."""
        self.rbac.create_role("temp", "Temporary", ["chat.send"])
        self.rbac.create_user("temp_user", "pass", role_name="temp")
        with pytest.raises(RBACError, match="users assigned"):
            self.rbac.delete_role("temp")

    def test_list_users(self):
        """Listing users should return all created users."""
        self.rbac.create_user("u1", "p1")
        self.rbac.create_user("u2", "p2")
        users = self.rbac.list_users()
        assert len(users) == 2

    def test_permission_check_inactive_user(self):
        """Inactive users should have no permissions."""
        user = self.rbac.create_user("deact", "pass", role_name="admin")
        assert self.rbac.check_permission(user.id, "admin.users")
        self.rbac.deactivate_user(user.id)
        assert not self.rbac.check_permission(user.id, "admin.users")

    def test_get_user_permissions(self):
        """Getting user permissions should return the role's permission set."""
        user = self.rbac.create_user("viewer1", "pass", role_name="viewer")
        perms = self.rbac.get_user_permissions(user.id)
        assert "chat.send" in perms
        assert "chat.history" in perms
        assert "tools.execute" not in perms
