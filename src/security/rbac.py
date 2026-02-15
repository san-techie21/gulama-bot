"""
Role-Based Access Control (RBAC) for Gulama.

Provides multi-user support with fine-grained permissions.
Users are assigned roles, and roles define what actions they can perform.

Roles hierarchy:
- admin: Full system access, can manage users and settings
- operator: Can use all tools, manage skills, view audit logs
- user: Can chat, use approved tools, view own data
- viewer: Read-only access (can chat but no tool execution)
- guest: Limited chat access, no tools
"""

from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.utils.logging import get_logger

logger = get_logger("rbac")


@dataclass
class Permission:
    """A single permission definition."""

    name: str
    description: str
    category: str  # "chat", "tools", "admin", "data", "system"


# All available permissions
PERMISSIONS: dict[str, Permission] = {
    # Chat permissions
    "chat.send": Permission("chat.send", "Send messages", "chat"),
    "chat.stream": Permission("chat.stream", "Use streaming responses", "chat"),
    "chat.history": Permission("chat.history", "View chat history", "chat"),
    # Tool permissions
    "tools.execute": Permission("tools.execute", "Execute tools/skills", "tools"),
    "tools.shell": Permission("tools.shell", "Execute shell commands", "tools"),
    "tools.file_read": Permission("tools.file_read", "Read files", "tools"),
    "tools.file_write": Permission("tools.file_write", "Write files", "tools"),
    "tools.network": Permission("tools.network", "Make network requests", "tools"),
    "tools.browser": Permission("tools.browser", "Use browser automation", "tools"),
    "tools.email": Permission("tools.email", "Send/read emails", "tools"),
    "tools.code_exec": Permission("tools.code_exec", "Execute code", "tools"),
    # Admin permissions
    "admin.users": Permission("admin.users", "Manage users", "admin"),
    "admin.roles": Permission("admin.roles", "Manage roles", "admin"),
    "admin.config": Permission("admin.config", "Change configuration", "admin"),
    "admin.skills": Permission("admin.skills", "Install/remove skills", "admin"),
    "admin.vault": Permission("admin.vault", "Access secrets vault", "admin"),
    # Data permissions
    "data.own": Permission("data.own", "View own data", "data"),
    "data.all": Permission("data.all", "View all users' data", "data"),
    "data.export": Permission("data.export", "Export data", "data"),
    "data.audit": Permission("data.audit", "View audit logs", "data"),
    # System permissions
    "system.start": Permission("system.start", "Start/stop the system", "system"),
    "system.monitor": Permission("system.monitor", "View system status", "system"),
    "system.update": Permission("system.update", "Update the system", "system"),
}


@dataclass
class Role:
    """A role with a set of permissions."""

    name: str
    description: str
    permissions: set[str] = field(default_factory=set)
    is_system: bool = False  # System roles can't be deleted


# Built-in roles
BUILT_IN_ROLES: dict[str, Role] = {
    "admin": Role(
        name="admin",
        description="Full system administrator",
        permissions=set(PERMISSIONS.keys()),
        is_system=True,
    ),
    "operator": Role(
        name="operator",
        description="Operations — all tools, manage skills, view audit",
        permissions={
            "chat.send",
            "chat.stream",
            "chat.history",
            "tools.execute",
            "tools.shell",
            "tools.file_read",
            "tools.file_write",
            "tools.network",
            "tools.browser",
            "tools.email",
            "tools.code_exec",
            "admin.skills",
            "data.own",
            "data.all",
            "data.audit",
            "system.monitor",
        },
        is_system=True,
    ),
    "user": Role(
        name="user",
        description="Standard user — chat and approved tools",
        permissions={
            "chat.send",
            "chat.stream",
            "chat.history",
            "tools.execute",
            "tools.file_read",
            "tools.network",
            "data.own",
            "system.monitor",
        },
        is_system=True,
    ),
    "viewer": Role(
        name="viewer",
        description="Read-only — chat but no tools",
        permissions={
            "chat.send",
            "chat.history",
            "data.own",
        },
        is_system=True,
    ),
    "guest": Role(
        name="guest",
        description="Guest — limited chat only",
        permissions={
            "chat.send",
        },
        is_system=True,
    ),
}


@dataclass
class User:
    """A Gulama user."""

    id: str
    username: str
    email: str = ""
    role_name: str = "user"
    password_hash: str = ""
    salt: str = ""
    is_active: bool = True
    created_at: str = ""
    last_login: str = ""
    channel_ids: dict[str, str] = field(default_factory=dict)  # channel -> channel-specific ID
    metadata: dict[str, Any] = field(default_factory=dict)


class RBACManager:
    """
    Manages users, roles, and permissions.

    Features:
    - User CRUD
    - Role management
    - Permission checking
    - Password hashing (scrypt)
    - Channel-to-user mapping (Telegram ID → User, Discord ID → User, etc.)
    """

    def __init__(self):
        self._roles: dict[str, Role] = {}
        self._users: dict[str, User] = {}
        self._channel_map: dict[str, str] = {}  # "telegram:123" → user_id
        self._load_builtin_roles()

    def _load_builtin_roles(self) -> None:
        """Load built-in roles."""
        for name, role in BUILT_IN_ROLES.items():
            self._roles[name] = Role(
                name=role.name,
                description=role.description,
                permissions=set(role.permissions),
                is_system=role.is_system,
            )

    # --- User Management ---

    def create_user(
        self,
        username: str,
        password: str,
        email: str = "",
        role_name: str = "user",
    ) -> User:
        """Create a new user."""
        if any(u.username == username for u in self._users.values()):
            raise RBACError(f"Username '{username}' already exists")
        if role_name not in self._roles:
            raise RBACError(f"Role '{role_name}' not found")

        salt = os.urandom(32).hex()
        password_hash = self._hash_password(password, salt)

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            role_name=role_name,
            password_hash=password_hash,
            salt=salt,
            created_at=datetime.now(UTC).isoformat(),
        )

        self._users[user.id] = user
        logger.info("user_created", username=username, role=role_name)
        return user

    def authenticate(self, username: str, password: str) -> User | None:
        """Authenticate a user by username and password."""
        user = next((u for u in self._users.values() if u.username == username), None)
        if not user or not user.is_active:
            return None

        expected_hash = self._hash_password(password, user.salt)
        if hmac.compare_digest(expected_hash, user.password_hash):
            user.last_login = datetime.now(UTC).isoformat()
            return user
        return None

    def get_user(self, user_id: str) -> User | None:
        """Get a user by ID."""
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> User | None:
        """Get a user by username."""
        return next((u for u in self._users.values() if u.username == username), None)

    def get_user_by_channel(self, channel: str, channel_user_id: str) -> User | None:
        """Get a user by their channel-specific ID."""
        key = f"{channel}:{channel_user_id}"
        user_id = self._channel_map.get(key)
        return self._users.get(user_id) if user_id else None

    def link_channel(self, user_id: str, channel: str, channel_user_id: str) -> None:
        """Link a channel-specific ID to a user."""
        user = self._users.get(user_id)
        if not user:
            raise RBACError(f"User '{user_id}' not found")

        key = f"{channel}:{channel_user_id}"
        self._channel_map[key] = user_id
        user.channel_ids[channel] = channel_user_id
        logger.info("channel_linked", user=user.username, channel=channel)

    def list_users(self) -> list[dict[str, Any]]:
        """List all users."""
        return [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role_name,
                "is_active": u.is_active,
                "created_at": u.created_at,
                "last_login": u.last_login,
            }
            for u in self._users.values()
        ]

    def update_user_role(self, user_id: str, new_role: str) -> None:
        """Change a user's role."""
        user = self._users.get(user_id)
        if not user:
            raise RBACError(f"User not found: {user_id}")
        if new_role not in self._roles:
            raise RBACError(f"Role not found: {new_role}")

        old_role = user.role_name
        user.role_name = new_role
        logger.info("user_role_changed", user=user.username, old=old_role, new=new_role)

    def deactivate_user(self, user_id: str) -> None:
        """Deactivate a user (soft delete)."""
        user = self._users.get(user_id)
        if user:
            user.is_active = False
            logger.info("user_deactivated", username=user.username)

    # --- Permission Checking ---

    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if a user has a specific permission."""
        user = self._users.get(user_id)
        if not user or not user.is_active:
            return False

        role = self._roles.get(user.role_name)
        if not role:
            return False

        return permission in role.permissions

    def get_user_permissions(self, user_id: str) -> set[str]:
        """Get all permissions for a user."""
        user = self._users.get(user_id)
        if not user or not user.is_active:
            return set()

        role = self._roles.get(user.role_name)
        return role.permissions if role else set()

    # --- Role Management ---

    def create_role(self, name: str, description: str, permissions: list[str]) -> Role:
        """Create a custom role."""
        if name in self._roles:
            raise RBACError(f"Role '{name}' already exists")

        # Validate permissions
        invalid = [p for p in permissions if p not in PERMISSIONS]
        if invalid:
            raise RBACError(f"Invalid permissions: {invalid}")

        role = Role(
            name=name,
            description=description,
            permissions=set(permissions),
        )
        self._roles[name] = role
        logger.info("role_created", name=name, permissions=len(permissions))
        return role

    def delete_role(self, name: str) -> None:
        """Delete a custom role."""
        role = self._roles.get(name)
        if not role:
            raise RBACError(f"Role not found: {name}")
        if role.is_system:
            raise RBACError(f"Cannot delete system role: {name}")

        # Check if any users have this role
        users_with_role = [u for u in self._users.values() if u.role_name == name]
        if users_with_role:
            raise RBACError(f"Cannot delete role '{name}' — {len(users_with_role)} users assigned")

        del self._roles[name]
        logger.info("role_deleted", name=name)

    def list_roles(self) -> list[dict[str, Any]]:
        """List all roles."""
        return [
            {
                "name": r.name,
                "description": r.description,
                "permissions": sorted(r.permissions),
                "is_system": r.is_system,
                "user_count": sum(1 for u in self._users.values() if u.role_name == r.name),
            }
            for r in self._roles.values()
        ]

    # --- Utilities ---

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Hash a password using scrypt."""
        return hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt),
            n=2**14,
            r=8,
            p=1,
            dklen=64,
        ).hex()


class RBACError(Exception):
    """Raised for RBAC-related errors."""

    pass
