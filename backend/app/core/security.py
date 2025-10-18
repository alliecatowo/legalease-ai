"""Security helpers for verifying Keycloak-issued tokens."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx
from authlib.jose import JsonWebKey, JsonWebToken, errors as jose_errors

from app.core.config import settings


class KeycloakOIDCVerifier:
    """Fetches OIDC metadata and verifies JWT access tokens."""

    def __init__(self) -> None:
        self._openid_configuration: Optional[Dict[str, Any]] = None
        self._openid_expires_at: float = 0
        self._jwks: Optional[Dict[str, Any]] = None
        self._jwks_expires_at: float = 0
        self._lock = asyncio.Lock()
        self._jwt = JsonWebToken(["RS256", "ES256"])

    @property
    def metadata_base_url(self) -> str:
        """URL to fetch OIDC metadata from (internal Keycloak URL)."""
        return f"{settings.KEYCLOAK_BASE_URL.rstrip('/')}/realms/{settings.KEYCLOAK_REALM}"

    @property
    def issuer(self) -> str:
        """Return the issuer URL for token validation.

        Note: Keycloak's issuer is based on its hostname config (KEYCLOAK_HOSTNAME),
        not the internal URL we use to fetch metadata. We need to match what Keycloak
        actually puts in the tokens.
        """
        # Keycloak uses auth.localhost as its hostname, so tokens have that issuer
        return "http://auth.localhost:8080/realms/legalease"

    @property
    def audience(self) -> Optional[str]:
        """Expected token audience."""
        return settings.KEYCLOAK_AUDIENCE or settings.KEYCLOAK_BACKEND_CLIENT_ID

    async def _fetch_openid_configuration(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=settings.KEYCLOAK_TIMEOUT_SECONDS) as client:
            # Fetch from internal URL, not the issuer URL
            response = await client.get(f"{self.metadata_base_url}/.well-known/openid-configuration")
            response.raise_for_status()
            return response.json()

    async def _fetch_jwks(self, jwks_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=settings.KEYCLOAK_TIMEOUT_SECONDS) as client:
            response = await client.get(jwks_uri)
            response.raise_for_status()
            return response.json()

    async def _ensure_metadata(self) -> None:
        now = time.time()
        async with self._lock:
            if self._openid_configuration is None or now >= self._openid_expires_at:
                self._openid_configuration = await self._fetch_openid_configuration()
                self._openid_expires_at = now + settings.KEYCLOAK_JWKS_CACHE_SECONDS

            if self._jwks is None or now >= self._jwks_expires_at:
                jwks_uri = self._openid_configuration["jwks_uri"]
                # Rewrite jwks_uri to use internal Keycloak URL for container-to-container requests
                # Keycloak returns URLs with its external hostname, but we need to use the internal one
                jwks_uri = jwks_uri.replace("auth.localhost:8080", "keycloak:8080")
                jwks_uri = jwks_uri.replace("auth.localhost", "keycloak:8080")
                self._jwks = await self._fetch_jwks(jwks_uri)
                self._jwks_expires_at = now + settings.KEYCLOAK_JWKS_CACHE_SECONDS

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT access token issued by Keycloak."""
        await self._ensure_metadata()
        assert self._jwks, "JWKS must be loaded"

        key_set = JsonWebKey.import_key_set(self._jwks)

        claims_params: Dict[str, Any] = {"iss": self.issuer}
        expected_aud = self.audience
        if expected_aud:
            claims_params["aud"] = expected_aud

        try:
            claims = self._jwt.decode(token, key_set, claims_params=claims_params)
            claims.validate()
        except jose_errors.ExpiredTokenError as exc:
            raise TokenVerificationError("Token has expired") from exc
        except jose_errors.InvalidClaimError as exc:
            raise TokenVerificationError(f"Invalid token claims: {exc}") from exc
        except jose_errors.JoseError as exc:
            raise TokenVerificationError("Unable to decode token") from exc

        # Normalise aud to list for easier downstream checks
        if "aud" in claims and isinstance(claims["aud"], str):
            claims["aud"] = [claims["aud"]]

        return dict(claims)


class TokenVerificationError(RuntimeError):
    """Raised when a JWT fails validation."""


oidc_verifier = KeycloakOIDCVerifier()
