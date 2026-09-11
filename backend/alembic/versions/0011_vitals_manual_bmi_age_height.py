"""add manual BMI/age/height inputs to vital_readings

Revision ID: 0011_vitals_manual_metrics
Revises: 0010_vitals_diabetes_pima_fields
Create Date: 2026-09-09

Adds optional height_cm / bmi / age_years so a reading can supply the
body-metric features (Age, BMI) and height manually instead of relying on
the patient profile. When blank, the profile-derived values are used.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_vitals_manual_metrics"
down_revision: Union[str, None] = "0010_vitals_diabetes_pima_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vital_readings",
        sa.Column("height_cm", sa.Float(), nullable=True),
    )
    op.add_column(
        "vital_readings",
        sa.Column("bmi", sa.Float(), nullable=True),
    )
    op.add_column(
        "vital_readings",
        sa.Column("age_years", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vital_readings", "age_years")
    op.drop_column("vital_readings", "bmi")
    op.drop_column("vital_readings", "height_cm")
