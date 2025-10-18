"""Keycloak admin service utilities."""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakAuthenticationError, KeycloakGetError

from app.core.config import settings


class KeycloakAdminService:
    """Lazy Keycloak admin client for realm management tasks."""

    _client: Optional[KeycloakAdmin] = None
    _lock = threading.Lock()

    def _build_client(self) -> KeycloakAdmin:
        if not settings.KEYCLOAK_BACKEND_CLIENT_SECRET:
            raise RuntimeError("KEYCLOAK_BACKEND_CLIENT_SECRET must be configured for admin access")

        return KeycloakAdmin(
            server_url=f"{settings.KEYCLOAK_BASE_URL.rstrip('/')}/",
            realm_name=settings.KEYCLOAK_REALM,
            client_id=settings.KEYCLOAK_BACKEND_CLIENT_ID,
            client_secret_key=settings.KEYCLOAK_BACKEND_CLIENT_SECRET,
            user_realm_name=settings.KEYCLOAK_REALM,
            verify=True,
        )

    @property
    def client(self) -> KeycloakAdmin:
        """Return a cached KeycloakAdmin instance."""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = self._build_client()
        return self._client

    def get_identity(self, keycloak_id: str) -> Dict[str, Any]:
        """Fetch identity details for a given Keycloak user ID."""
        try:
            return self.client.get_user(user_id=keycloak_id)
        except KeycloakGetError as exc:
            raise RuntimeError(f"Failed to fetch user {keycloak_id}: {exc}") from exc

    def list_user_groups(self, keycloak_id: str) -> List[Dict[str, Any]]:
        """Return the groups a user belongs to."""
        try:
            return self.client.get_user_groups(user_id=keycloak_id)
        except KeycloakGetError as exc:
            raise RuntimeError(f"Failed to fetch groups for {keycloak_id}: {exc}") from exc

    def get_group_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """Retrieve a group by its canonical path (/teams/<slug>)."""
        try:
            return self.client.get_group_by_path(path=path)
        except KeycloakGetError as exc:
            if exc.response_code == 404:
                return None
            raise RuntimeError(f"Failed to load group {path}: {exc}") from exc

    def update_user(self, keycloak_id: str, updates: Dict[str, Any]) -> None:
        """Update user attributes in Keycloak.

        Args:
            keycloak_id: The Keycloak user ID
            updates: Dictionary of user attributes to update (e.g., firstName, lastName, email)
        """
        try:
            self.client.update_user(user_id=keycloak_id, payload=updates)
        except KeycloakGetError as exc:
            raise RuntimeError(f"Failed to update user {keycloak_id}: {exc}") from exc

    def health_check(self) -> bool:
        """Verify that the service account can authenticate."""
        try:
            _ = self.client.connection.token
            return True
        except KeycloakAuthenticationError as exc:
            raise RuntimeError(f"Keycloak authentication failed: {exc}") from exc
