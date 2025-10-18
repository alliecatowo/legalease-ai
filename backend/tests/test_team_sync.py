from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.user import TeamMembership, TeamRole, User
from app.services.auth.sync import TeamSynchronizer


class MockAdminService:
    def __init__(self, team_id: UUID):
        self.group_id = 'mock-group-id'
        self.team_id = team_id

    def get_group_by_path(self, path: str, search_in_subgroups: bool = True):
        if path != '/teams/example':
            return None
        return {
            'id': self.group_id,
            'name': 'Example Team',
            'attributes': {
                'team_id': [str(self.team_id)],
                'membership_role': ['ADMIN']
            }
        }


def create_session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    return TestingSession()


def test_team_synchronizer_creates_membership_and_active_team():
    db = create_session()

    try:
        team_id = uuid4()
        user = User(
            keycloak_id=uuid4(),
            email='user@example.com'
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        syncer = TeamSynchronizer(cache_ttl=0)
        syncer._admin = MockAdminService(team_id)

        syncer.sync_memberships(
            db,
            user,
            group_paths=['/teams/example'],
            active_team_claim=str(team_id)
        )

        db.commit()
        db.refresh(user)

        assert user.active_team_id == team_id
        assert len(user.memberships) == 1
        membership: TeamMembership = user.memberships[0]
        assert membership.role == TeamRole.ADMIN
        assert membership.team_id == team_id
    finally:
        db.close()
