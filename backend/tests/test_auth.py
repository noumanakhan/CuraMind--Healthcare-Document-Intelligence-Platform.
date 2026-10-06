import os
import tempfile

# Use a dedicated throwaway database before importing the application/settings.
TEST_DATABASE = os.path.join(tempfile.gettempdir(), "curamind-auth-tests.sqlite3")
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///" + TEST_DATABASE
os.environ["JWT_SECRET"] = "test-secret-with-more-than-thirty-two-characters"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["ALLOW_PUBLIC_REGISTRATION"] = "true"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db
from app.main import app
from app.models import User, Workspace
from app.core.security import hash_password

TEST_ENGINE = create_engine("sqlite:///" + TEST_DATABASE, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_signup_defaults_to_viewer_and_authenticates(client):
    response = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "long-test-password-1",
        "role": "admin",
    })
    assert response.status_code == 201
    result = response.json()
    assert result["user"]["role"] == "viewer"
    assert "password_hash" not in result["user"]
    assert "curamind_refresh" in client.cookies

    me = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + result["access_token"]})
    assert me.status_code == 200
    assert me.json()["email"] == "test@example.com"

    denied = client.get("/api/v1/users", headers={"Authorization": "Bearer " + result["access_token"]})
    assert denied.status_code == 403


def test_login_refresh_rotation_and_logout(client):
    signup = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "long-test-password-1",
    })
    assert signup.status_code == 201
    original_cookie = client.cookies.get("curamind_refresh")

    login = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "long-test-password-1"})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "viewer"

    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    assert client.cookies.get("curamind_refresh") != original_cookie

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_invalid_login_does_not_disclose_account_existence(client):
    unknown = client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": "wrong-password"})
    assert unknown.status_code == 401
    created = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "known@example.com",
        "password": "long-test-password-1",
    })
    wrong = client.post("/api/v1/auth/login", json={"email": "known@example.com", "password": "wrong-password"})
    assert wrong.status_code == unknown.status_code
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_admin_can_assign_roles_and_deactivate_users(client):
    db = TestSession()
    workspace = db.query(Workspace).filter(Workspace.name == "CuraMind Workspace").first()
    if workspace is None:
        workspace = Workspace(name="CuraMind Workspace")
        db.add(workspace)
        db.flush()
    admin = User(workspace_id=workspace.id, email="admin@example.com", name="Admin", password_hash=hash_password("admin-test-password-1"), role="admin", is_active=True)
    db.add(admin)
    db.commit()
    db.close()

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-test-password-1"})
    assert admin_login.status_code == 200
    token = admin_login.json()["access_token"]
    headers = {"Authorization": "Bearer " + token}

    registered = client.post("/api/v1/auth/register", json={
        "name": "Clinician",
        "email": "clinician@example.com",
        "password": "clinician-test-password-1",
    })
    user_id = registered.json()["user"]["id"]
    role_update = client.patch("/api/v1/users/{}/role".format(user_id), json={"role": "clinician"}, headers=headers)
    assert role_update.status_code == 200
    assert role_update.json()["role"] == "clinician"

    disabled = client.patch("/api/v1/users/{}/status".format(user_id), json={"is_active": False}, headers=headers)
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False

    disabled_login = client.post("/api/v1/auth/login", json={"email": "clinician@example.com", "password": "clinician-test-password-1"})
    assert disabled_login.status_code == 401


def test_hardcoded_admin_login(client):
    from app.main import ensure_hardcoded_admin
    db = TestSession()
    ensure_hardcoded_admin(db)
    db.close()

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin@gmail.com", "password": "allahmuhammad"})
    assert admin_login.status_code == 200
    user_data = admin_login.json()["user"]
    assert user_data["email"] == "admin@gmail.com"
    assert user_data["role"] == "admin"

