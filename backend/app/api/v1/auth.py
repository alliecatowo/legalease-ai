"""Authentication and team management endpoints."""

from __future__ import annotations

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
    UserProfileResponse,
)

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
        active=user.active,
        active_team=active_team_summary,
        memberships=memberships,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    """Return the authenticated user's profile."""
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

    return _build_profile_response(current_user)
