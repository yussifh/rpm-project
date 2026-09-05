"""add data_source to risk_predictions

Revision ID: 0005_prediction_source
Revises: 0004_vitals_weight
Create Date: 2026-08-04

Adds risk_predictions.data_source so the UI can show whether a given
prediction came from a model trained on real patient data or on
synthetic (simulated) data — see app/ai_engine/feature_schema.py for the
per-disease provenance this reflects.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_prediction_source"
down_revision: Union[str, None] = "0004_vitals_weight"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "risk_predictions",
        sa.Column("data_source", sa.String(length=80), nullable=False, server_default="unknown"),
    )
    op.alter_column("risk_predictions", "data_source", server_default=None)


def downgrade() -> None:
    op.drop_column("risk_predictions", "data_source")
