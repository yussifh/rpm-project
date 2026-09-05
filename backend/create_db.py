"""Create all tables directly from models (bypasses Alembic for SQLite dev)."""
import sys
sys.path.insert(0, ".")

from app.db.session import engine, Base
import app.models  # noqa: F401 — registers all models

Base.metadata.create_all(bind=engine)
print("All tables created successfully!")
