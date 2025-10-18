"""Debug endpoints for testing."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_bearer_token, get_current_user
from app.core.database import get_db
from app.core.security import oidc_verifier
from app.models.user import Team, User

router = APIRouter()


@router.get("/token-claims")
async def show_token_claims(token: str = Depends(get_bearer_token)):
    """Show what's in the current access token."""
    try:
        claims = await oidc_verifier.verify_token(token)
        return {
            "claims": claims,
            "has_groups": "groups" in claims,
            "groups": claims.get("groups", []),
            "has_active_team": "active_team" in claims,
            "active_team": claims.get("active_team"),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/sync-teams")
async def force_team_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Force a team sync and return current teams."""
    # The get_current_user dependency already runs team sync
    # Just return the current state
    teams = db.query(Team).all()
    return {
        "user_email": current_user.email,
        "user_memberships": len(current_user.memberships),
        "total_teams": len(teams),
        "teams": [
            {
                "id": str(t.id),
                "name": t.name,
                "slug": t.slug,
                "keycloak_group_id": t.keycloak_group_id,
            }
            for t in teams
        ],
        "user_teams": [
            {
                "id": str(m.team.id),
                "name": m.team.name,
                "role": m.role,
            }
            for m in current_user.memberships
        ],
    }
