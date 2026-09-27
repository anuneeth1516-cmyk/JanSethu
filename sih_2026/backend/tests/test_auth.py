import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import PROBLEMS, app
from app.models import User, UserRole
from app.security import hash_password, verify_password


@pytest.fixture(name="db_session")
def db_session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(name="client")
def client_fixture(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==========================================
# 1. User Registration Tests
# ==========================================
def test_user_registration_success(client):
    payload = {
        "name": "Ananya Sharma",
        "email": "ananya@example.org",
        "password": "SecurePassword123!",
        "role": "citizen",
        "bio": "Civic enthusiast",
        "location": "Vijayawada, AP",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "ananya@example.org"
    assert data["user"]["role"] == "citizen"
    assert data["user"]["profile"]["display_name"] == "Ananya Sharma"


def test_duplicate_email_registration_rejected(client):
    payload = {
        "name": "Ananya Sharma",
        "email": "duplicate@example.org",
        "password": "SecurePassword123!",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    # Attempt second registration with same email
    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"]


def test_invalid_auth_payloads_return_400(client):
    bad_register = client.post(
        "/api/v1/auth/register",
        json={"name": "", "email": "not-an-email", "password": "short"},
    )
    assert bad_register.status_code == 400

    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": ""},
    )
    assert bad_login.status_code == 400


def test_password_never_stored_in_plaintext(client, db_session):
    plain_password = "SuperSecretPassword99!"
    payload = {
        "name": "Security Test User",
        "email": "security@example.org",
        "password": plain_password,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    user = db_session.query(User).filter_by(email="security@example.org").first()
    assert user is not None
    assert user.password_hash != plain_password
    assert not user.password_hash.startswith(plain_password)
    assert user.password_hash.startswith("$argon2")
    assert verify_password(plain_password, user.password_hash)


# ==========================================
# 2. Login Tests
# ==========================================
def test_user_login_success(client):
    reg_payload = {
        "name": "Login User",
        "email": "login_test@example.org",
        "password": "CorrectPassword123!",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "login_test@example.org",
        "password": "CorrectPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login_test@example.org"


def test_login_wrong_password_rejected(client):
    reg_payload = {
        "name": "Wrong Pass User",
        "email": "wrongpass@example.org",
        "password": "CorrectPassword123!",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "wrongpass@example.org",
        "password": "WrongPassword456!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_nonexistent_email_rejected(client):
    login_payload = {
        "email": "ghost@example.org",
        "password": "AnyPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401


# ==========================================
# 3. Current User (/api/v1/auth/me) Tests
# ==========================================
def test_get_current_user_authenticated(client):
    reg_payload = {
        "name": "Me Endpoint User",
        "email": "me@example.org",
        "password": "Password123!",
        "role": "student",
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.org"
    assert data["role"] == "student"
    assert data["profile"]["display_name"] == "Me Endpoint User"


def test_get_current_user_missing_token_rejected(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_current_user_invalid_token_rejected(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert response.status_code == 401


def test_logout_endpoint(client):
    reg_payload = {
        "name": "Logout User",
        "email": "logout@example.org",
        "password": "Password123!",
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]

    response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "Logged out successfully" in response.json()["message"]


# ==========================================
# 4. Roles & Extensibility Tests
# ==========================================
@pytest.mark.parametrize(
    "role_input,expected_role",
    [
        ("citizen", "citizen"),
        ("user", "citizen"),
        ("student", "student"),
        ("researcher", "researcher"),
        ("university_researcher", "researcher"),
        ("university", "university"),
        ("company", "company"),
        ("ngo", "ngo"),
        ("ngo_organization", "ngo"),
        ("expert", "expert"),
        ("authority", "authority"),
        ("authority_admin", "admin"),
        ("admin", "admin"),
    ],
)
def test_roles_extensible_and_normalized(client, role_input, expected_role):
    email = f"role_{role_input}@example.org"
    reg_payload = {
        "name": f"User {role_input}",
        "email": email,
        "password": "Password123!",
        "role": role_input,
    }
    response = client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 201
    assert response.json()["user"]["role"] == expected_role


# ==========================================
# 5. Role-based Authorization Tests
# ==========================================
def test_admin_route_forbidden_for_regular_citizen(client):
    citizen_reg = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Regular Citizen",
            "email": "regular@example.org",
            "password": "Password123!",
            "role": "citizen",
        },
    )
    citizen_token = citizen_reg.json()["access_token"]

    # Citizen tries accessing admin endpoint
    response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {citizen_token}"})
    assert response.status_code == 403
    assert "Action requires" in response.json()["detail"] or "Insufficient permissions" in response.json()["detail"]


def test_admin_route_allowed_for_admin(client):
    admin_reg = client.post(
        "/api/v1/auth/register",
        json={
            "name": "System Admin",
            "email": "admin@example.org",
            "password": "AdminPassword123!",
            "role": "admin",
        },
    )
    admin_token = admin_reg.json()["access_token"]

    response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ==========================================
# 6. Resource Ownership Tests
# ==========================================
def test_ownership_enforcement_on_modify_and_delete(client):
    # Register User A
    user_a = client.post(
        "/api/v1/auth/register",
        json={
            "name": "User A",
            "email": "usera@example.org",
            "password": "Password123!",
        },
    ).json()
    token_a = user_a["access_token"]
    user_a_id = user_a["user"]["id"]

    # Register User B
    user_b = client.post(
        "/api/v1/auth/register",
        json={
            "name": "User B",
            "email": "userb@example.org",
            "password": "Password123!",
        },
    ).json()
    token_b = user_b["access_token"]

    # Register Admin
    admin_res = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Super Admin",
            "email": "owner_admin@example.org",
            "password": "Password123!",
            "role": "admin",
        },
    ).json()
    admin_token = admin_res["access_token"]

    # Create a problem owned by User A
    problem_id = "owned-problem-1"
    PROBLEMS.insert(
        0,
        {
            "id": problem_id,
            "title": "Road pothole issue",
            "description": "Deep pothole on corner",
            "creator_id": user_a_id,
            "place": "Vijayawada",
            "severity": "Medium",
            "urgency": "Soon",
            "reports": 1,
            "status": "Analysis",
            "tags": ["Roads"],
            "progress": 5,
        },
    )

    # 1. User B (not owner) tries to modify User A's problem -> 403 Forbidden
    res_b_update = client.put(
        f"/api/v1/problems/{problem_id}",
        json={"title": "Hacked Title"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_update.status_code == 403

    # 2. User B (not owner) tries to delete User A's problem -> 403 Forbidden
    res_b_delete = client.delete(
        f"/api/v1/problems/{problem_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_delete.status_code == 403

    # 3. User A (owner) updates problem -> 200 OK
    res_a_update = client.put(
        f"/api/v1/problems/{problem_id}",
        json={"title": "Updated Road Pothole by Owner"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a_update.status_code == 200
    assert res_a_update.json()["title"] == "Updated Road Pothole by Owner"

    # 4. Admin deletes problem -> 200 OK
    res_admin_delete = client.delete(
        f"/api/v1/problems/{problem_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin_delete.status_code == 200
    assert res_admin_delete.json()["status"] == "deleted"
