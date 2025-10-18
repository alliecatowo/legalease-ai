"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenVerificationError, oidc_verifier
from app.models.user import Team, User
from app.services.auth.sync import TeamSynchronizer


logger = logging.getLogger(__name__)
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
        logger.debug("Token extracted from bearer credentials (prefix: %s...)", token[:20])
    elif "Authorization" in request.headers:
        # Support raw tokens without the HTTP bearer helper
        header_value = request.headers.get("Authorization")
        if header_value and header_value.lower().startswith("bearer "):
            token = header_value[7:].strip()
            logger.debug("Token extracted from Authorization header (prefix: %s...)", token[:20])

    if not token:
        # Allow token propagation via cookie (SSO with BFF)
        token = request.cookies.get("kc_access_token")
        if token:
            logger.debug("Token extracted from kc_access_token cookie (prefix: %s...)", token[:20])

    if not token:
        logger.warning("No access token found - Headers: %s, Cookies: %s", list(request.headers.keys()), list(request.cookies.keys()))
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
    logger.debug("Validating bearer token (prefix: %s...)", token[:20])
    try:
        logger.debug("Verifying token with OIDC verifier")
        claims = await oidc_verifier.verify_token(token)
        logger.info("Token verified successfully - subject: %s, email: %s", claims.get("sub"), claims.get("email"))
    except TokenVerificationError as exc:
        logger.warning("Token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error during token verification: %s: %s", type(exc).__name__, exc, exc_info=True)
        raise

    # Require valid 'sub' claim with UUID format
    subject = claims.get("sub")
    if not subject:
        logger.error("Token missing required 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required 'sub' claim - ensure Keycloak client has 'sub' claim mapper configured",
        )

    try:
        keycloak_id = uuid.UUID(subject)
        logger.debug("Parsed keycloak_id from 'sub' claim: %s", keycloak_id)
    except ValueError as exc:
        logger.error("'sub' claim is not a valid UUID: %s", subject)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token 'sub' claim is not a valid UUID: {subject}",
        ) from exc

    # Look up user by keycloak_id
    logger.debug("Looking up user with keycloak_id: %s", keycloak_id)
    user = db.query(User).filter(User.keycloak_id == keycloak_id).first()

    if not user:
        # JIT create new user with keycloak_id from 'sub' claim
        email = claims.get("email")
        user = User(
            keycloak_id=keycloak_id,
            email=email or "unknown@example.com",
            full_name=claims.get("name") or claims.get("preferred_username"),
        )
        db.add(user)
        logger.info("Created new user with keycloak_id: %s, email: %s", keycloak_id, email)
    else:
        updated = False
        email = claims.get("email")
        if email and user.email != email:
            user.email = email
            updated = True
            logger.debug("Updated email for user %s", keycloak_id)
        full_name = claims.get("name") or claims.get("preferred_username")
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            updated = True
            logger.debug("Updated full_name for user %s", keycloak_id)
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
