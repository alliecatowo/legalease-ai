"""Security helpers for verifying Keycloak-issued tokens."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from authlib.jose import JsonWebKey, JsonWebToken, errors as jose_errors

from app.core.config import settings


logger = logging.getLogger(__name__)


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
        return f"{settings.KEYCLOAK_INTERNAL_URL.rstrip('/')}/realms/{settings.KEYCLOAK_REALM}"

    @property
    def issuer(self) -> str:
        """Return the issuer URL for token validation.

        Note: Keycloak's issuer is based on its hostname config (KEYCLOAK_HOSTNAME),
        not the internal URL we use to fetch metadata. We need to match what Keycloak
        actually puts in the tokens.
        """
        return f"{settings.KEYCLOAK_PUBLIC_URL.rstrip('/')}/realms/{settings.KEYCLOAK_REALM}"

    @property
    def audience(self) -> Optional[str]:
        """Expected token audience."""
        return settings.KEYCLOAK_AUDIENCE or settings.KEYCLOAK_BACKEND_CLIENT_ID

    async def _fetch_openid_configuration(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=settings.KEYCLOAK_TIMEOUT_SECONDS) as client:
            # Fetch from internal URL, not the issuer URL
            url = f"{self.metadata_base_url}/.well-known/openid-configuration"
            logger.debug("Fetching OIDC metadata from %s", url)
            try:
                response = await client.get(url)
                response.raise_for_status()
                logger.info("Successfully fetched OIDC metadata")
                return response.json()
            except httpx.HTTPError as exc:
                logger.error("Failed to fetch OIDC metadata from %s: %s", url, exc)
                raise

    async def _fetch_jwks(self, jwks_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=settings.KEYCLOAK_TIMEOUT_SECONDS) as client:
            logger.debug("Fetching JWKS from %s", jwks_uri)
            try:
                response = await client.get(jwks_uri)
                response.raise_for_status()
                logger.info("Successfully fetched JWKS")
                return response.json()
            except httpx.HTTPError as exc:
                logger.error("Failed to fetch JWKS from %s: %s", jwks_uri, exc)
                raise

    async def _ensure_metadata(self) -> None:
        now = time.time()
        async with self._lock:
            if self._openid_configuration is None or now >= self._openid_expires_at:
                logger.debug("OIDC configuration cache expired or empty, refreshing")
                self._openid_configuration = await self._fetch_openid_configuration()
                self._openid_expires_at = now + settings.KEYCLOAK_JWKS_CACHE_SECONDS

            if self._jwks is None or now >= self._jwks_expires_at:
                logger.debug("JWKS cache expired or empty, refreshing")
                jwks_uri = self._openid_configuration["jwks_uri"]
                # Rewrite jwks_uri to use internal Keycloak URL for container-to-container requests
                # Keycloak returns URLs with its public hostname, but we need to use the internal one
                public_base = f"{settings.KEYCLOAK_PUBLIC_URL.rstrip('/')}/realms/{settings.KEYCLOAK_REALM}"
                internal_base = f"{settings.KEYCLOAK_INTERNAL_URL.rstrip('/')}/realms/{settings.KEYCLOAK_REALM}"
                jwks_uri = jwks_uri.replace(public_base, internal_base)
                logger.debug("Rewritten JWKS URI from %s to internal URL", jwks_uri)
                self._jwks = await self._fetch_jwks(jwks_uri)
                self._jwks_expires_at = now + settings.KEYCLOAK_JWKS_CACHE_SECONDS

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT access token issued by Keycloak."""
        logger.debug("Verifying token (prefix: %s...)", token[:20])
        await self._ensure_metadata()
        assert self._jwks, "JWKS must be loaded"

        key_set = JsonWebKey.import_key_set(self._jwks)

        claims_params: Dict[str, Any] = {"iss": self.issuer}
        expected_aud = self.audience
        if expected_aud:
            claims_params["aud"] = expected_aud

        logger.debug("Validating token with issuer: %s, audience: %s", self.issuer, expected_aud)

        try:
            claims = self._jwt.decode(token, key_set, claims_params=claims_params)
            claims.validate()
            logger.debug("Token decoded and validated successfully")
        except jose_errors.ExpiredTokenError as exc:
            logger.warning("Token verification failed: token has expired")
            raise TokenVerificationError("Token has expired") from exc
        except jose_errors.InvalidClaimError as exc:
            logger.warning("Token verification failed: invalid claims - %s", exc)
            raise TokenVerificationError(f"Invalid token claims: {exc}") from exc
        except jose_errors.JoseError as exc:
            logger.warning("Token verification failed: unable to decode - %s", exc)
            raise TokenVerificationError("Unable to decode token") from exc

        # Normalise aud to list for easier downstream checks
        if "aud" in claims and isinstance(claims["aud"], str):
            claims["aud"] = [claims["aud"]]

        return dict(claims)


class TokenVerificationError(RuntimeError):
    """Raised when a JWT fails validation."""


oidc_verifier = KeycloakOIDCVerifier()
