"""add emergency_contact_notified to alerts

Revision ID: 0008_emergency_contact_notified
Revises: 0007_assistant_messages
Create Date: 2026-08-14

Adds alerts.emergency_contact_notified — set True when a CRITICAL alert
triggers a (simulated) notification to the patient's emergency contact.
See app/services/emergency_contact_service.py.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_emergency_contact_notified"
down_revision: Union[str, None] = "0007_assistant_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "alerts",
        sa.Column("emergency_contact_notified", sa.Boolean, nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("alerts", "emergency_contact_notified")
