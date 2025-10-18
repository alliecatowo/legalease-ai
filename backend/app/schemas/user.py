"""Pydantic schemas for auth, users, and teams."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import TeamRole


class TeamSummary(BaseModel):
    """Lightweight representation of a team."""

    id: UUID
    name: str
    slug: str
    description: Optional[str] = None


class TeamMembershipResponse(BaseModel):
    """Team membership with the caller's role."""

    team: TeamSummary
    role: TeamRole
    joined_at: datetime = Field(alias="created_at")

    class Config:
        populate_by_name = True


class UserProfileResponse(BaseModel):
    """Current authenticated user profile."""

    id: UUID
    keycloak_id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    active: bool
    active_team: Optional[TeamSummary] = None
    memberships: list[TeamMembershipResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class UpdateActiveTeamRequest(BaseModel):
    """Request payload for switching the active team."""

    team_id: UUID


class UpdateUserProfileRequest(BaseModel):
    """Request payload for updating user profile."""

    full_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=64, pattern=r'^[a-zA-Z0-9_-]+$')
    bio: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = Field(None, max_length=512)

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Jane Doe",
                "username": "janedoe",
                "bio": "Legal professional with 10 years of experience",
                "avatar_url": "https://example.com/avatar.jpg"
            }
        }


class UserPublicProfile(BaseModel):
    """Public-facing user profile information."""

    id: UUID
    username: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


class UserBasicInfoResponse(BaseModel):
    """Lightweight user info for /me endpoint."""

    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class AuditLogEntry(BaseModel):
    """Audit record entry."""

    id: UUID
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    payload: Optional[dict] = None
    created_at: datetime


class TeamCreateRequest(BaseModel):
    """Admin request for creating a team."""

    name: str
    slug: str
    description: Optional[str] = None


class InviteUserRequest(BaseModel):
    """Request to invite a new user to a team."""

    email: EmailStr
    full_name: Optional[str] = None
    role: TeamRole = TeamRole.MEMBER
