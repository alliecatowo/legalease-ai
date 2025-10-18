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
    UpdateUserProfileRequest,
    UserBasicInfoResponse,
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

    # Update fields that were provided
    if request.full_name is not None:
        current_user.full_name = request.full_name
    if request.username is not None:
        current_user.username = request.username
    if request.bio is not None:
        current_user.bio = request.bio
    if request.avatar_url is not None:
        current_user.avatar_url = request.avatar_url

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

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
