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
        print(f"[AUTH DEBUG] Got token from credentials: {token[:20]}...")
    elif "Authorization" in request.headers:
        # Support raw tokens without the HTTP bearer helper
        header_value = request.headers.get("Authorization")
        if header_value and header_value.lower().startswith("bearer "):
            token = header_value[7:].strip()
            print(f"[AUTH DEBUG] Got token from header: {token[:20]}...")

    if not token:
        # Allow token propagation via cookie (SSO with BFF)
        token = request.cookies.get("kc_access_token")
        if token:
            print(f"[AUTH DEBUG] Got token from cookie: {token[:20]}...")

    if not token:
        print(f"[AUTH DEBUG] No token found! Headers: {list(request.headers.keys())}, Cookies: {list(request.cookies.keys())}")
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
    print(f"[AUTH DEBUG] get_current_user called with token: {token[:50]}...")
    try:
        print(f"[AUTH DEBUG] About to verify token...")
        claims = await oidc_verifier.verify_token(token)
        print(f"[AUTH DEBUG] Token verified! All claims: {claims}")
    except TokenVerificationError as exc:
        print(f"[AUTH DEBUG] Token verification failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        print(f"[AUTH DEBUG] Unexpected error during token verification: {type(exc).__name__}: {exc}")
        raise

    # Try to get subject - Keycloak should include 'sub' but fallback to email
    subject = claims.get("sub")
    email = claims.get("email")
    print(f"[AUTH DEBUG] Subject: {subject}, Email: {email}")

    if not subject and not email:
        print(f"[AUTH DEBUG] ERROR: No subject or email in claims!")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    # Try to find user by keycloak_id (UUID) or by email
    user = None
    if subject:
        try:
            identity_id = uuid.UUID(subject)
            print(f"[AUTH DEBUG] Looking up user with keycloak_id: {identity_id}")
            user = db.query(User).filter(User.keycloak_id == identity_id).first()
        except ValueError:
            print(f"[AUTH DEBUG] Subject is not a UUID: {subject}")

    # Fallback to email lookup
    if not user and email:
        print(f"[AUTH DEBUG] Looking up user by email: {email}")
        user = db.query(User).filter(User.email == email).first()

    print(f"[AUTH DEBUG] User found: {user is not None}")
    if not user:
        # Create new user - use subject as keycloak_id if it's a UUID, otherwise generate one from email
        import hashlib

        if subject:
            try:
                kc_id = uuid.UUID(subject)
                print(f"[AUTH DEBUG] Using subject as keycloak_id: {kc_id}")
            except ValueError:
                # Subject is not a UUID, generate one based on email
                email_for_hash = email or "unknown"
                email_hash = hashlib.sha256(email_for_hash.encode()).hexdigest()
                kc_id = uuid.UUID(email_hash[:32])
                print(f"[AUTH DEBUG] Generated keycloak_id from email: {kc_id}")
        else:
            # No subject claim, generate from email
            email_for_hash = email or "unknown"
            email_hash = hashlib.sha256(email_for_hash.encode()).hexdigest()
            kc_id = uuid.UUID(email_hash[:32])
            print(f"[AUTH DEBUG] No subject, generated keycloak_id from email: {kc_id}")

        user = User(
            keycloak_id=kc_id,
            email=email or "unknown@example.com",
            full_name=claims.get("name") or claims.get("preferred_username"),
        )
        db.add(user)
        print(f"[AUTH DEBUG] Created new user with keycloak_id: {kc_id}")
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
