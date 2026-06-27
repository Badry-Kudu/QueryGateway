"""Add allow_unauthenticated to endpoints

Forces public (unauthenticated) data endpoints to be an explicit choice
(audit finding M1). Existing rows backfill to ``false`` via the server
default, so they keep being served — the data plane logs a
``public_endpoint_served`` warning — while any future edit must opt in.

Revision ID: a8307fb20816
Revises: 0001
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8307fb20816"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "endpoints",
        sa.Column(
            "allow_unauthenticated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("endpoints", "allow_unauthenticated")
