"""add assistant_messages

Revision ID: 0007_assistant_messages
Revises: 0006_remove_doctor
Create Date: 2026-08-12

Adds the `assistant_messages` table backing the AI Health Assistant chat
(see app/services/assistant_service.py) — the feature that replaced
patient<->doctor messaging when the doctor role was removed.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_assistant_messages"
down_revision: Union[str, None] = "0006_remove_doctor"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "patient_id",
            sa.String(36),
            sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_emergency_override", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_assistant_messages_patient_id", "assistant_messages", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_assistant_messages_patient_id", table_name="assistant_messages")
    op.drop_table("assistant_messages")
