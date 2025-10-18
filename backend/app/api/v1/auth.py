"""Authentication and team management endpoints."""

from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import Team, TeamMembership, TeamRole, User
from app.schemas.user import (
    TeamMembershipResponse,
    TeamSummary,
    UpdateActiveTeamRequest,
    UpdateUserProfileRequest,
    UserBasicInfoResponse,
    UserProfileResponse,
)
from app.services.auth.keycloak import KeycloakAdminService

logger = logging.getLogger(__name__)
keycloak_admin = KeycloakAdminService()

router = APIRouter()


def _team_to_summary(team: Team) -> TeamSummary:
    return TeamSummary(
        id=team.id,
        name=team.name,
        slug=team.slug,
        description=team.description,
    )


def _membership_to_response(membership: TeamMembership) -> TeamMembershipResponse:
    return TeamMembershipResponse(
        team=_team_to_summary(membership.team),
        role=membership.role,
        created_at=membership.created_at,
    )


def _build_profile_response(user: User) -> UserProfileResponse:
    active_team_summary = _team_to_summary(user.active_team) if user.active_team else None
    memberships = [
        _membership_to_response(membership)
        for membership in sorted(user.memberships, key=lambda m: m.created_at)
    ]
    return UserProfileResponse(
        id=user.id,
        keycloak_id=user.keycloak_id,
        email=user.email,
        full_name=user.full_name,
        username=user.username,
        avatar_url=user.avatar_url,
        bio=user.bio,
        active=user.active,
        active_team=active_team_summary,
        memberships=memberships,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/me", response_model=UserBasicInfoResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserBasicInfoResponse:
    """Return lightweight basic info for the current user."""
    return UserBasicInfoResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
    )


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    """Return the authenticated user's profile."""
    return _build_profile_response(current_user)


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    request: UpdateUserProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """Update the authenticated user's profile."""
    # Check if username is being changed and if it's already taken
    if request.username is not None and request.username != current_user.username:
        existing_user = db.query(User).filter(User.username == request.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

    # Track if we need to update Keycloak
    keycloak_updates = {}

    # Update fields that were provided
    if request.full_name is not None:
        current_user.full_name = request.full_name
        # Parse full_name into firstName and lastName for Keycloak
        # Split on first space: "John Doe" -> firstName="John", lastName="Doe"
        parts = request.full_name.strip().split(maxsplit=1)
        keycloak_updates["firstName"] = parts[0] if parts else ""
        keycloak_updates["lastName"] = parts[1] if len(parts) > 1 else ""

    if request.username is not None:
        current_user.username = request.username
    if request.bio is not None:
        current_user.bio = request.bio
    if request.avatar_url is not None:
        current_user.avatar_url = request.avatar_url

    # Update local database first
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    # Sync to Keycloak if full_name was changed
    if keycloak_updates:
        try:
            logger.info(
                "Syncing user profile to Keycloak for user %s: %s",
                current_user.keycloak_id,
                keycloak_updates,
            )
            keycloak_admin.update_user(str(current_user.keycloak_id), keycloak_updates)
            logger.info("Successfully synced profile to Keycloak for user %s", current_user.keycloak_id)
        except Exception as exc:
            logger.error(
                "Failed to sync profile to Keycloak for user %s: %s",
                current_user.keycloak_id,
                exc,
                exc_info=True,
            )
            # Don't fail the request if Keycloak sync fails - the local DB is already updated
            # This ensures the user can still update their profile even if Keycloak is down

    return _build_profile_response(current_user)


@router.get("/teams", response_model=List[TeamMembershipResponse])
async def list_teams(current_user: User = Depends(get_current_user)) -> List[TeamMembershipResponse]:
    """Return all teams the current user belongs to."""
    return [
        _membership_to_response(membership)
        for membership in sorted(current_user.memberships, key=lambda m: m.created_at)
    ]


@router.post("/switch-team", response_model=UserProfileResponse)
async def switch_active_team(
    request: UpdateActiveTeamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """Update the active team for the current user."""
    membership = next((m for m in current_user.memberships if m.team_id == request.team_id), None)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not belong to the requested team.",
        )

    current_user.active_team_id = request.team_id
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    # Sync the active_team attribute to Keycloak so future tokens include it
    try:
        logger.info(
            "Syncing active_team to Keycloak for user %s: %s",
            current_user.keycloak_id,
            request.team_id,
        )
        keycloak_admin.update_user(
            str(current_user.keycloak_id),
            {"attributes": {"active_team": str(request.team_id)}},
        )
        logger.info(
            "Successfully synced active_team to Keycloak for user %s",
            current_user.keycloak_id,
        )
    except Exception as exc:
        logger.error(
            "Failed to sync active_team to Keycloak for user %s: %s",
            current_user.keycloak_id,
            exc,
            exc_info=True,
        )
        # Don't fail the request if Keycloak sync fails - the local DB is already updated
        # The user can still switch teams, but future tokens may not include the updated active_team
        # until the next token refresh

    return _build_profile_response(current_user)
