"""
SSO / SAML / OAuth integration for Gulama Enterprise.

Supports:
- SAML 2.0 (enterprise SSO)
- OAuth 2.0 / OpenID Connect (social/cloud login)
- API key authentication (for automated access)

This module provides the authentication backends that can be
plugged into the gateway's auth middleware.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.utils.logging import get_logger

logger = get_logger("sso")


@dataclass
class SSOConfig:
    """SSO configuration."""
    provider: str  # "saml", "oidc", "oauth2", "apikey"
    client_id: str = ""
    client_secret: str = ""
    issuer_url: str = ""
    redirect_uri: str = "http://127.0.0.1:18789/auth/callback"
    scopes: list[str] = field(default_factory=lambda: ["openid", "profile", "email"])
    # SAML-specific
    saml_metadata_url: str = ""
    saml_entity_id: str = ""


@dataclass
class SSOUser:
    """User information from SSO provider."""
    external_id: str
    email: str
    name: str = ""
    provider: str = ""
    groups: list[str] = field(default_factory=list)
    raw_claims: dict[str, Any] = field(default_factory=dict)


class OIDCProvider:
    """
    OpenID Connect / OAuth 2.0 authentication provider.

    Supports:
    - Google Workspace
    - Microsoft Entra ID (Azure AD)
    - Okta
    - Auth0
    - Any OIDC-compliant provider
    """

    def __init__(self, config: SSOConfig):
        self.config = config
        self._well_known: dict[str, Any] | None = None

    async def get_authorization_url(self, state: str | None = None) -> str:
        """Generate the authorization URL for SSO login."""
        well_known = await self._get_well_known()
        auth_endpoint = well_known.get("authorization_endpoint", "")

        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
        }

        return f"{auth_endpoint}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        well_known = await self._get_well_known()
        token_endpoint = well_known.get("token_endpoint", "")

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.config.redirect_uri,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> SSOUser:
        """Get user information from the OIDC provider."""
        well_known = await self._get_well_known()
        userinfo_endpoint = well_known.get("userinfo_endpoint", "")

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            claims = response.json()

        return SSOUser(
            external_id=claims.get("sub", ""),
            email=claims.get("email", ""),
            name=claims.get("name", claims.get("preferred_username", "")),
            provider=self.config.provider,
            groups=claims.get("groups", []),
            raw_claims=claims,
        )

    async def _get_well_known(self) -> dict[str, Any]:
        """Fetch OIDC well-known configuration."""
        if self._well_known:
            return self._well_known

        url = f"{self.config.issuer_url}/.well-known/openid-configuration"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            self._well_known = response.json()
            return self._well_known


class SAMLProvider:
    """
    SAML 2.0 authentication provider.

    Provides basic SAML SSO flow:
    1. Generate AuthnRequest
    2. Redirect to IdP
    3. Process SAML Response
    4. Extract user attributes

    Note: Full SAML support requires the 'python3-saml' library.
    """

    def __init__(self, config: SSOConfig):
        self.config = config

    async def get_login_url(self) -> str:
        """Get the SAML login redirect URL."""
        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
            # Full SAML implementation would go here
            return f"{self.config.saml_metadata_url}/login"
        except ImportError:
            logger.warning("saml_not_available", msg="Install python3-saml for SAML support")
            return ""

    async def process_response(self, saml_response: str) -> SSOUser | None:
        """Process SAML response and extract user info."""
        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
            # Full SAML response processing would go here
            # This is a simplified version
            return None
        except ImportError:
            logger.warning("saml_not_available")
            return None


class APIKeyAuth:
    """
    API key authentication for programmatic access.

    Generates and validates API keys for automated systems
    and integrations.
    """

    def __init__(self):
        self._keys: dict[str, dict[str, Any]] = {}  # key_hash → metadata

    def generate_key(
        self,
        user_id: str,
        name: str = "default",
        expires_in_days: int = 365,
    ) -> str:
        """Generate a new API key."""
        # Generate key: gulama_sk_<random>
        key = f"gulama_sk_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(key)

        self._keys[key_hash] = {
            "user_id": user_id,
            "name": name,
            "created_at": time.time(),
            "expires_at": time.time() + (expires_in_days * 86400),
            "last_used": None,
        }

        logger.info("api_key_created", user_id=user_id, name=name)
        return key

    def validate_key(self, key: str) -> dict[str, Any] | None:
        """Validate an API key and return its metadata."""
        key_hash = self._hash_key(key)
        meta = self._keys.get(key_hash)

        if not meta:
            return None

        # Check expiration
        if time.time() > meta["expires_at"]:
            logger.warning("api_key_expired", user_id=meta["user_id"])
            return None

        meta["last_used"] = time.time()
        return meta

    def revoke_key(self, key: str) -> bool:
        """Revoke an API key."""
        key_hash = self._hash_key(key)
        if key_hash in self._keys:
            del self._keys[key_hash]
            return True
        return False

    def list_keys(self, user_id: str) -> list[dict[str, Any]]:
        """List API keys for a user (without the actual keys)."""
        return [
            {
                "name": meta["name"],
                "created_at": meta["created_at"],
                "expires_at": meta["expires_at"],
                "last_used": meta["last_used"],
            }
            for meta in self._keys.values()
            if meta["user_id"] == user_id
        ]

    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()


class SSOManager:
    """
    Manages all SSO providers and authentication methods.
    """

    def __init__(self):
        self._providers: dict[str, Any] = {}
        self._api_key_auth = APIKeyAuth()

    def configure_oidc(self, name: str, config: SSOConfig) -> None:
        """Configure an OIDC provider."""
        self._providers[name] = OIDCProvider(config)
        logger.info("oidc_configured", name=name, issuer=config.issuer_url)

    def configure_saml(self, name: str, config: SSOConfig) -> None:
        """Configure a SAML provider."""
        self._providers[name] = SAMLProvider(config)
        logger.info("saml_configured", name=name)

    def get_provider(self, name: str) -> Any:
        """Get an SSO provider by name."""
        return self._providers.get(name)

    @property
    def api_keys(self) -> APIKeyAuth:
        """Get the API key authentication handler."""
        return self._api_key_auth

    def list_providers(self) -> list[dict[str, str]]:
        """List configured SSO providers."""
        return [
            {
                "name": name,
                "type": type(provider).__name__,
            }
            for name, provider in self._providers.items()
        ]
