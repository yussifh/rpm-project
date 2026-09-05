"""add risk_predictions.recommendations

Revision ID: 0009_prediction_recommendations
Revises: 0008_emergency_contact_notified
Create Date: 2026-08-15

Adds risk_predictions.recommendations — a short, prioritized list of
clinically-grounded, patient-specific recommendations generated alongside
each prediction's `reasons` (see app/services/recommendation_engine.py).
Mirrors the existing `reasons` column exactly (same JSONB-array-of-
strings shape, same server_default), added in 0003_disease_workflow.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009_prediction_recommendations"
down_revision: Union[str, None] = "0008_emergency_contact_notified"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "risk_predictions",
        sa.Column("recommendations", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("risk_predictions", "recommendations")
