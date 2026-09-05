"""
Shared pytest fixtures.

Design decision: tests run against an in-memory SQLite DB, not the real
Postgres container. This keeps unit/integration tests for business logic
fast and isolated. A smaller set of true end-to-end tests (against real
Postgres via docker-compose) can be added later in a separate CI job if
Postgres-specific behavior (JSONB, etc.) needs verification.
"""

import fakeredis
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 ensures all models are registered before Base.metadata.create_all
from app.api.deps import get_current_user, get_db
from app.core.security import hash_password
from app.db.redis_client import get_redis
from app.db.session import Base
from app.models.admin import AdminProfile
from app.models.enums import UserRole
from app.models.user import User

# Import the FastAPI app instance LAST. `import app.models` above binds the
# name `app` in this module to the top-level `app` package; importing the
# FastAPI instance as `app` before that import would get silently
# shadowed, breaking `app.dependency_overrides` in the fixtures below.
from app.main import app as app  # noqa: E402


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def redis_client():
    return fakeredis.FakeStrictRedis(decode_responses=True)


@pytest.fixture()
def client(db_session, redis_client):
    from fastapi.testclient import TestClient

    def _get_db_override():
        yield db_session

    def _get_redis_override():
        return redis_client

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_redis] = _get_redis_override

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# --- Shared auth helpers/fixtures (used across multiple test modules) ---

PATIENT_PAYLOAD = {
    "email": "patient1@example.com",
    "password": "SecurePass123",
    "full_name": "Patient One",
    "date_of_birth": "1985-03-20",
    "gender": "male",
}


def seed_admin(db_session) -> User:
    """
    Note on bootstrapping: there is deliberately NO public "create first
    admin" API endpoint (that would be a serious security hole). In
    production the first admin is created via a seed script / management
    command. This helper mirrors that same out-of-band bootstrap process.
    """
    admin = User(
        email="admin@example.com",
        hashed_password=hash_password("AdminPass123"),
        full_name="System Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    admin.admin_profile = AdminProfile(is_super_admin=True)
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


def login(client, email, password):
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_token(client, db_session):
    seed_admin(db_session)
    return login(client, "admin@example.com", "AdminPass123")


@pytest.fixture()
def patient_token(client, admin_token):
    """Patients are created by an admin now — there is no public
    self-registration endpoint (see api/v1/auth.py). This fixture mirrors
    that real workflow rather than the old public /auth/register call."""
    resp = client.post("/api/v1/admin/users/patient", json=PATIENT_PAYLOAD, headers=auth_headers(admin_token))
    assert resp.status_code == 201, resp.text
    return login(client, PATIENT_PAYLOAD["email"], PATIENT_PAYLOAD["password"])
