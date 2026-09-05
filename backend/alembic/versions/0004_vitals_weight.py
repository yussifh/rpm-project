"""add weight_kg to vital_readings

Revision ID: 0004_vitals_weight
Revises: 0003_disease_workflow
Create Date: 2026-08-04

Adds vital_readings.weight_kg (nullable float). Weight is a shared signal
across all three tracked conditions (stroke, diabetes, hypertension) rather
than being specific to one, so it's added as a general vitals column —
same pattern as spo2_percent / temperature_celsius in 0001.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_vitals_weight"
down_revision: Union[str, None] = "0003_disease_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vital_readings",
        sa.Column("weight_kg", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vital_readings", "weight_kg")
