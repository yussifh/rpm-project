"""add primary_condition, disease_assessments, prediction reasons

Revision ID: 0003_disease_workflow
Revises: 0002_messages
Create Date: 2026-07-26

Adds:
  - patient_profiles.primary_condition (nullable, reuses the existing
    `disease_type` Postgres enum type created in 0001)
  - disease_assessments table (patient symptom checklist submissions)
  - risk_predictions.reasons (explainable-AI human-readable reasons list)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_disease_workflow"
down_revision: Union[str, None] = "0002_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Reuse the existing `disease_type` enum type (created in 0001) —
    # create_type=False so Alembic doesn't try to CREATE TYPE again.
    disease_type_enum = postgresql.ENUM(
        "stroke", "diabetes", "hypertension", name="disease_type", create_type=False
    )

    op.add_column(
        "patient_profiles",
        sa.Column("primary_condition", disease_type_enum, nullable=True),
    )

    op.create_table(
        "disease_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "patient_id",
            sa.String(36),
            sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("disease_type", disease_type_enum, nullable=False),
        sa.Column("symptoms", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_disease_assessments_patient_id", "disease_assessments", ["patient_id"])

    op.add_column(
        "risk_predictions",
        sa.Column("reasons", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("risk_predictions", "reasons")
    op.drop_index("ix_disease_assessments_patient_id", table_name="disease_assessments")
    op.drop_table("disease_assessments")
    op.drop_column("patient_profiles", "primary_condition")
