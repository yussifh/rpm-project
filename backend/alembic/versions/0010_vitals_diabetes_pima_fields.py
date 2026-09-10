"""add Pima diabetes vitals fields to vital_readings

Revision ID: 0010_vitals_diabetes_pima_fields
Revises: 0009_prediction_recommendations
Create Date: 2026-09-09

Adds the three extra measurements the diabetes risk model now consumes
(see app/ai_engine/feature_schema.py DIABETES_FEATURES) — skin thickness,
fasting serum insulin, and the diabetes pedigree function. These map
one-to-one to the Pima Indians Diabetes dataset columns the model is
trained on. All nullable since not every reading includes them.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_vitals_diabetes_pima_fields"
down_revision: Union[str, None] = "0009_prediction_recommendations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vital_readings",
        sa.Column("skin_thickness_mm", sa.Float(), nullable=True),
    )
    op.add_column(
        "vital_readings",
        sa.Column("serum_insulin_mu_u_ml", sa.Float(), nullable=True),
    )
    op.add_column(
        "vital_readings",
        sa.Column("diabetes_pedigree_function", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vital_readings", "diabetes_pedigree_function")
    op.drop_column("vital_readings", "serum_insulin_mu_u_ml")
    op.drop_column("vital_readings", "skin_thickness_mm")