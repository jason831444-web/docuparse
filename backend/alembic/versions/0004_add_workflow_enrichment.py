"""add workflow enrichment

Revision ID: 0004_add_workflow_enrichment
Revises: 0003_add_provider_tracking
Create Date: 2026-04-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_add_workflow_enrichment"
down_revision: str | None = "0003_add_provider_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("workflow_summary", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("action_items", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False))
    op.add_column("documents", sa.Column("warnings", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False))
    op.add_column("documents", sa.Column("key_dates", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False))
    op.add_column("documents", sa.Column("urgency_level", sa.String(length=20), nullable=True))
    op.add_column("documents", sa.Column("follow_up_required", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("documents", sa.Column("workflow_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.alter_column("documents", "action_items", server_default=None)
    op.alter_column("documents", "warnings", server_default=None)
    op.alter_column("documents", "key_dates", server_default=None)
    op.alter_column("documents", "follow_up_required", server_default=None)


def downgrade() -> None:
    op.drop_column("documents", "workflow_metadata")
    op.drop_column("documents", "follow_up_required")
    op.drop_column("documents", "urgency_level")
    op.drop_column("documents", "key_dates")
    op.drop_column("documents", "warnings")
    op.drop_column("documents", "action_items")
    op.drop_column("documents", "workflow_summary")
