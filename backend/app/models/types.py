"""
Shared portable column types.

`PortableJSON` behaves like Postgres JSONB in production (indexable,
efficient binary storage) but falls back to plain JSON on any other
dialect — notably SQLite, which the test suite uses for fast, isolated
runs. Using `postgresql.JSONB` directly breaks table creation on SQLite
with `CompileError: can't render element of type JSONB`.

`str_enum_column(...)` fixes a related, much nastier trap: SQLAlchemy's
`Enum` type, given a Python `(str, enum.Enum)` class, binds and reads
back using each member's `.name` (e.g. "ADMIN") by default — NOT its
`.value` (e.g. "admin") — unless `values_callable` is set. Every enum in
this codebase is defined with lowercase `.value`s (see app/models/enums.py)
and the Alembic migration creates the native Postgres ENUM types using
those same lowercase values. Without `values_callable`, SQLAlchemy tries
to INSERT "ADMIN" into a Postgres enum that only permits "admin", failing
with `DataError: invalid input value for enum user_role: "ADMIN"`.
This is invisible under SQLite (used by the test suite), because SQLite
has no native enum type — SQLAlchemy compiles it as a VARCHAR + CHECK
constraint built from those same `.name`s, so bind value and constraint
stay self-consistent even though both are silently wrong relative to the
Postgres schema. Always build enum columns via this helper, not `Enum(...)`
directly.
"""

from sqlalchemy import JSON, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator, CHAR


class PortableUUID(TypeDecorator):
    """UUID value stored consistently as a 36-character string.

    The project's Alembic schema defines UUID primary/foreign-key columns as
    VARCHAR(36) on PostgreSQL. Keeping the ORM on the same representation
    avoids uuid-vs-varchar comparison errors while still exposing uuid.UUID
    objects to Python code.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, str):
            import uuid
            return uuid.UUID(value)
        return value

    @property
    def python_type(self):
        import uuid
        return uuid.UUID


PortableJSON = JSON().with_variant(JSONB(), "postgresql")


def str_enum_column(enum_cls, name: str):
    """Enum column that binds/reads using `.value`, matching both the
    Alembic-created Postgres enum type and the enum's own string values."""
    return Enum(enum_cls, name=name, values_callable=lambda obj: [e.value for e in obj])
