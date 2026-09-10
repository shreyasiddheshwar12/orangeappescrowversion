import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "orange_test")
os.environ.setdefault("JWT_SECRET", "ci-test-secret")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("SEED_ENABLED", "false")

from fastapi.testclient import TestClient

import app as orange_app

server = orange_app.server


def route_exists(path, method):
    return any(
        getattr(route, "path", None) == path and method in getattr(route, "methods", set())
        for route in server.app.routes
    )


def test_hardening_layer_loaded():
    assert getattr(server.app.state, "e2e_hardened", False) is True
    assert route_exists("/api/auth/instagram/connect", "GET")
    assert route_exists("/api/auth/instagram/callback", "GET")
    assert route_exists("/api/auth/instagram/status", "GET")
    assert route_exists("/api/auth/instagram/disconnect", "POST")
    assert route_exists("/api/uploads", "POST")
    assert route_exists("/api/campaigns/{campaign_id}/pay", "POST")


def test_oauth_configuration_error_is_actionable():
    client = TestClient(server.app)
    response = client.get("/api/auth/instagram/connect")
    assert response.status_code in {401, 403}


def test_upload_requires_authentication():
    client = TestClient(server.app)
    response = client.post("/api/uploads")
    assert response.status_code in {401, 403}
