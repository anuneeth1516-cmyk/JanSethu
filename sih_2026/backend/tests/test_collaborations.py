import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import CollaborationRequest, Profile, User


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
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register_user(client, email, name="Requester"):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "Password123!", "role": "citizen"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_collaboration_request_lifecycle_uses_real_match_and_recipient_permissions(client, db_session):
    requester = register_user(client, "collaboration-requester@example.org")
    requester_headers = {"Authorization": f"Bearer {requester['access_token']}"}
    problem = client.post(
        "/api/v1/problems",
        json={
            "title": "Water access problem",
            "description": "Residents need community assessment and field research for a water access issue.",
        },
        headers=requester_headers,
    )
    assert problem.status_code == 201, problem.text
    problem_data = problem.json()
    assert problem_data["matches"]
    recipient_id = problem_data["matches"][0]["candidate_id"]
    recipient = db_session.get(User, recipient_id)
    assert recipient is not None

    unauthenticated = client.get("/api/v1/collaborations")
    assert unauthenticated.status_code == 401

    create_response = client.post(
        "/api/v1/collaborations",
        json={"problem_id": problem_data["id"], "recipient_id": recipient_id, "message": "Please join this problem."},
        headers=requester_headers,
    )
    assert create_response.status_code == 201, create_response.text
    request_data = create_response.json()
    assert request_data["requester_id"] == requester["user"]["id"]
    assert request_data["recipient_id"] == recipient_id
    assert request_data["status"] == "pending"
    assert request_data["collaborator"]["candidate_id"] == recipient_id
    assert request_data["collaborator"]["email"] == recipient.email
    assert "password_hash" not in request_data["collaborator"]
    assert db_session.query(CollaborationRequest).filter_by(id=request_data["id"]).one().requester_id == requester["user"]["id"]

    duplicate = client.post(
        "/api/v1/collaborations",
        json={"problem_id": problem_data["id"], "recipient_id": recipient_id},
        headers=requester_headers,
    )
    assert duplicate.status_code == 409

    deleted = client.delete(f"/api/v1/collaborations/{request_data['id']}", headers=requester_headers)
    assert deleted.status_code == 204
    recreated = client.post(
        "/api/v1/collaborations",
        json={"problem_id": problem_data["id"], "recipient_id": recipient_id, "message": "Please join this problem again."},
        headers=requester_headers,
    )
    assert recreated.status_code == 201, recreated.text
    request_data = recreated.json()
    assert request_data["status"] == "pending"

    requester_requests = client.get("/api/v1/collaborations", headers=requester_headers)
    assert requester_requests.status_code == 200
    assert any(item["id"] == request_data["id"] for item in requester_requests.json())

    recipient_login = client.post(
        "/api/v1/auth/login",
        json={"email": recipient.email, "password": "Development123!"},
    )
    assert recipient_login.status_code == 200, recipient_login.text
    recipient_headers = {"Authorization": f"Bearer {recipient_login.json()['access_token']}"}

    accepted = client.patch(
        f"/api/v1/collaborations/{request_data['id']}",
        json={"status": "accepted"},
        headers=recipient_headers,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"

    requester_cannot_modify = client.patch(
        f"/api/v1/collaborations/{request_data['id']}",
        json={"status": "rejected"},
        headers=requester_headers,
    )
    assert requester_cannot_modify.status_code == 403

    recipient_requests = client.get("/api/v1/collaborations", headers=recipient_headers)
    assert recipient_requests.status_code == 200
    assert any(item["id"] == request_data["id"] and item["status"] == "accepted" for item in recipient_requests.json())
