"""Synchronize Keycloak group membership with local team records."""

from __future__ import annotations

import time
import uuid
from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from app.models.user import Team, TeamMembership, TeamRole, User
from app.services.auth.keycloak import KeycloakAdminService


class TeamSynchronizer:
    """Sync user team membership from Keycloak groups into Postgres."""

    def __init__(self, cache_ttl: int = 300) -> None:
        self._admin = KeycloakAdminService()
        self._cache_ttl = cache_ttl
        self._group_cache: Dict[str, tuple[float, dict]] = {}

    def _get_group(self, path: str) -> Optional[dict]:
        now = time.time()
        cached = self._group_cache.get(path)
        if cached and now < cached[0]:
            return cached[1]

        group = self._admin.get_group_by_path(path)
        if group:
            self._group_cache[path] = (now + self._cache_ttl, group)
        return group

    def _extract_team_id(self, group: dict, path: str) -> uuid.UUID:
        attributes = group.get("attributes") or {}
        team_ids = attributes.get("team_id") or attributes.get("teamId")
        if team_ids:
            try:
                return uuid.UUID(team_ids[0])
            except (ValueError, TypeError):
                pass
        # Deterministic fallback based on group path
        return uuid.uuid5(uuid.NAMESPACE_URL, path)

    def _derive_role(self, group: dict) -> TeamRole:
        attributes = group.get("attributes") or {}
        role_values = attributes.get("membership_role") or attributes.get("team_role")
        if role_values:
            try:
                return TeamRole(role_values[0].upper())
            except (ValueError, AttributeError, IndexError):
                return TeamRole.MEMBER
        return TeamRole.MEMBER

    def sync_memberships(
        self,
        db: Session,
        user: User,
        group_paths: Iterable[str],
        active_team_claim: Optional[str],
    ) -> None:
        """Ensure local memberships mirror the groups found in the access token."""
        existing_memberships = {membership.team_id: membership for membership in user.memberships}
        retained_team_ids: set[uuid.UUID] = set()

        for path in group_paths:
            if not path.startswith("/teams/"):
                continue

            group = self._get_group(path)
            if not group:
                continue

            slug = path.split("/")[-1]
            team_id = self._extract_team_id(group, path)
            team = db.get(Team, team_id)
            if not team:
                team = Team(
                    id=team_id,
                    keycloak_group_id=group.get("id"),
                    name=group.get("name") or slug.replace("-", " ").title(),
                    slug=slug,
                    description=(group.get("attributes") or {}).get("description", [None])[0],
                )
                db.add(team)
            else:
                team.name = group.get("name") or team.name
                team.keycloak_group_id = team.keycloak_group_id or group.get("id")

            membership = existing_memberships.get(team_id)
            if membership is None:
                membership = TeamMembership(
                    team=team,
                    user=user,
                    role=self._derive_role(group),
                )
                db.add(membership)
                user.memberships.append(membership)
            else:
                membership.role = self._derive_role(group)

            retained_team_ids.add(team_id)

        # Remove memberships that are no longer present
        for team_id, membership in existing_memberships.items():
            if team_id not in retained_team_ids:
                db.delete(membership)

        if not retained_team_ids:
            user.active_team_id = None
            return

        active_team_id: Optional[uuid.UUID] = None
        if active_team_claim:
            try:
                possible_id = uuid.UUID(active_team_claim)
                if possible_id in retained_team_ids:
                    active_team_id = possible_id
            except (ValueError, TypeError):
                active_team_id = None

        if active_team_id is None:
            # Fallback: keep existing active team if still valid otherwise pick first team
            if user.active_team_id in retained_team_ids:
                active_team_id = user.active_team_id
            else:
                active_team_id = next(iter(retained_team_ids))

        user.active_team_id = active_team_id
