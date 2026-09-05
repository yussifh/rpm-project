"""remove doctor role, appointments, messages

Revision ID: 0006_remove_doctor
Revises: 0005_prediction_source
Create Date: 2026-08-11

This project no longer has a Doctor role — the system is Patient + Admin
only, with the AI/ML models as the prediction engine and an AI Health
Assistant (planned separately) replacing doctor-patient messaging.

Drops, in FK-dependency order:
  - appointments table (patient<->doctor scheduling; meaningless without
    a doctor role)
  - messages table (patient<->doctor care-thread messaging; superseded by
    the AI Health Assistant)
  - alerts.doctor_id (alerts are now visible to patient + admin only)
  - medications.prescribed_by_id (patients self-report their own
    medication list; there's no doctor to prescribe it)
  - patient_profiles.assigned_doctor_id
  - doctor_profiles table
  - the doctor_profiles-dependent enum value on user_role, and the
    appointment_status enum type entirely

Postgres can't drop a single value from an existing ENUM type in one
statement pre-PG12 semantics reliably across all managed providers, so we
rebuild `user_role` the safe, portable way: create a new enum type with
just the values we want, swap the column over via USING cast, drop the
old type, rename the new one into place.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_remove_doctor"
down_revision: Union[str, None] = "0005_prediction_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- drop tables that only existed for the doctor relationship ---
    op.drop_index("ix_messages_patient_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_scheduled_at", table_name="appointments")
    op.drop_table("appointments")

    # --- drop doctor-referencing columns ---
    op.drop_constraint("alerts_doctor_id_fkey", "alerts", type_="foreignkey")
    op.drop_column("alerts", "doctor_id")

    op.drop_constraint("medications_prescribed_by_id_fkey", "medications", type_="foreignkey")
    op.drop_column("medications", "prescribed_by_id")

    op.drop_constraint("patient_profiles_assigned_doctor_id_fkey", "patient_profiles", type_="foreignkey")
    op.drop_column("patient_profiles", "assigned_doctor_id")

    # --- drop doctor_profiles table itself ---
    op.drop_table("doctor_profiles")

    # --- rebuild user_role enum without 'doctor' ---
    op.execute("CREATE TYPE user_role_new AS ENUM ('admin', 'patient')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role_new "
        "USING role::text::user_role_new"
    )
    op.execute("DROP TYPE user_role")
    op.execute("ALTER TYPE user_role_new RENAME TO user_role")

    # --- drop the now-unused appointment_status enum type ---
    postgresql.ENUM(name="appointment_status").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # --- restore user_role enum with 'doctor' ---
    op.execute("CREATE TYPE user_role_new AS ENUM ('admin', 'doctor', 'patient')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role_new "
        "USING role::text::user_role_new"
    )
    op.execute("DROP TYPE user_role")
    op.execute("ALTER TYPE user_role_new RENAME TO user_role")

    # --- recreate doctor_profiles ---
    op.create_table(
        "doctor_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("specialization", sa.String(150), nullable=False),
        sa.Column("license_number", sa.String(100), nullable=False, unique=True),
        sa.Column("years_of_experience", sa.Integer, nullable=True),
        sa.Column("hospital_affiliation", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- restore doctor-referencing columns ---
    op.add_column(
        "patient_profiles",
        sa.Column(
            "assigned_doctor_id",
            sa.String(36),
            sa.ForeignKey("doctor_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "medications",
        sa.Column(
            "prescribed_by_id",
            sa.String(36),
            sa.ForeignKey("doctor_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "alerts",
        sa.Column(
            "doctor_id",
            sa.String(36),
            sa.ForeignKey("doctor_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # --- recreate appointments ---
    op.create_table(
        "appointments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "patient_id",
            sa.String(36),
            sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "doctor_id",
            sa.String(36),
            sa.ForeignKey("doctor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum("scheduled", "completed", "cancelled", "no_show", name="appointment_status"),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_appointments_scheduled_at", "appointments", ["scheduled_at"])
    op.create_index("ix_appointments_status", "appointments", ["status"])

    # --- recreate messages ---
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "patient_id",
            sa.String(36),
            sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_patient_id", "messages", ["patient_id"])
