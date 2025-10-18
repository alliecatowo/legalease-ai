"""add auth and team tables

Revision ID: 5c3bf9d9f8a2
Revises: 2407377fe923
Create Date: 2024-09-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "5c3bf9d9f8a2"
down_revision: Union[str, Sequence[str], None] = "2407377fe923"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply auth schema changes."""
    teamrole_enum = postgresql.ENUM("OWNER", "ADMIN", "MEMBER", name="teamrole")
    teamrole_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("keycloak_group_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keycloak_group_id", name="uq_teams_keycloak_group_id"),
    )
    op.create_index(op.f("ix_teams_slug"), "teams", ["slug"], unique=True)
    op.create_index(op.f("ix_teams_keycloak_group_id"), "teams", ["keycloak_group_id"], unique=True)

    # Attach cases to teams
    op.add_column("cases", sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_cases_team_id"), "cases", ["team_id"], unique=False)
    op.create_foreign_key(
        "fk_cases_team_id",
        source_table="cases",
        referent_table="teams",
        local_cols=["team_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("keycloak_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("active_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["active_team_id"], ["teams.id"], name="fk_users_active_team_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keycloak_id", name="uq_users_keycloak_id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index(op.f("ix_users_keycloak_id"), "users", ["keycloak_id"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_active_team_id"), "users", ["active_team_id"], unique=False)

    op.create_table(
        "team_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", teamrole_enum, nullable=False, server_default="MEMBER"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], name="fk_team_memberships_team_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_team_memberships_user_id", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_memberships_team_user"),
    )
    op.create_index(op.f("ix_team_memberships_team_id"), "team_memberships", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_memberships_user_id"), "team_memberships", ["user_id"], unique=False)

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("identity_provider_session_id", sa.String(length=255), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_sessions_user_id", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_user_sessions_session_id"),
    )
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_sessions_session_id"), "user_sessions", ["session_id"], unique=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=True),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], name="fk_audit_logs_team_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_audit_logs_user_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_team_id"), "audit_logs", ["team_id"], unique=False)


def downgrade() -> None:
    """Rollback auth schema changes."""
    op.drop_index(op.f("ix_audit_logs_team_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_user_sessions_session_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index(op.f("ix_team_memberships_user_id"), table_name="team_memberships")
    op.drop_index(op.f("ix_team_memberships_team_id"), table_name="team_memberships")
    op.drop_table("team_memberships")

    op.drop_index(op.f("ix_users_active_team_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_keycloak_id"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_teams_keycloak_group_id"), table_name="teams")
    op.drop_index(op.f("ix_teams_slug"), table_name="teams")
    op.drop_constraint("fk_cases_team_id", "cases", type_="foreignkey")
    op.drop_index(op.f("ix_cases_team_id"), table_name="cases")
    op.drop_column("cases", "team_id")

    op.drop_table("teams")

    teamrole_enum = postgresql.ENUM("OWNER", "ADMIN", "MEMBER", name="teamrole")
    teamrole_enum.drop(op.get_bind(), checkfirst=True)
