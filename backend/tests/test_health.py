"""
Smoke test — verifies the FastAPI app boots and the health endpoint
responds correctly. This is the first test in the suite; more are added
per-module (auth, vitals, predictions, etc.) as those modules are built.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
