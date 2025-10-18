"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenVerificationError, oidc_verifier
from app.models.user import Team, User
from app.services.auth.sync import TeamSynchronizer


bearer_scheme = HTTPBearer(auto_error=False)
team_syncer = TeamSynchronizer(cache_ttl=300)


async def get_bearer_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    """Extract the bearer token from the Authorization header or cookie."""
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    elif "Authorization" in request.headers:
        # Support raw tokens without the HTTP bearer helper
        header_value = request.headers.get("Authorization")
        if header_value and header_value.lower().startswith("bearer "):
            token = header_value[7:].strip()

    if not token:
        # Allow token propagation via cookie (SSO with BFF)
        token = request.cookies.get("kc_access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
        )

    return token


async def get_current_user(
    token: str = Depends(get_bearer_token),
    db: Session = Depends(get_db),
) -> User:
    """Validate the bearer token and ensure a local user exists."""
    try:
        claims = await oidc_verifier.verify_token(token)
    except TokenVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    subject = claims.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    try:
        identity_id = uuid.UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subject identifier",
        ) from exc

    user = db.query(User).filter(User.keycloak_id == identity_id).first()
    if not user:
        user = User(
            keycloak_id=identity_id,
            email=claims.get("email") or f"user-{identity_id}@placeholder.local",
            full_name=claims.get("name") or claims.get("preferred_username"),
        )
        db.add(user)
    else:
        updated = False
        email = claims.get("email")
        if email and user.email != email:
            user.email = email
            updated = True
        full_name = claims.get("name") or claims.get("preferred_username")
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            updated = True
        if updated:
            db.add(user)

    groups = claims.get("groups") or []
    active_team_claim = claims.get("active_team")

    team_syncer.sync_memberships(db, user, groups, active_team_claim)

    db.flush()
    return user


def require_active_team(user: User = Depends(get_current_user)) -> Team:
    """Ensure the user has an active team selection."""
    if not user.active_team:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active team selected",
        )
    return user.active_team
