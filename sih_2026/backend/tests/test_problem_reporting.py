import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import AIAnalysis, Match, Problem, Profile, Support, User


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


def register_user(client, email, password="Password123!", role="citizen", name="Test User"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_authenticated_problem_creation_persists_and_returns_db_record(client, db_session):
    user = register_user(client, "creator@example.org")
    token = user["access_token"]

    response = client.post(
        "/api/v1/problems",
        json={
            "title": "Blocked drainage channel",
            "description": "Water is pooling after rain and flooding the lane near the clinic.",
            "category": "infrastructure",
            "location_text": "Main Road, Sector 7",
            "latitude": 17.385,
            "longitude": 78.4867,
            "metadata": {"hazard": "flooding"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == "Blocked drainage channel"
    assert data["description"] == "Water is pooling after rain and flooding the lane near the clinic."
    assert data["creator_id"] == user["user"]["id"]
    assert data["location"]["latitude"] == 17.385
    assert data["location"]["longitude"] == 78.4867

    saved = db_session.query(Problem).filter_by(id=data["id"]).one()
    assert saved.creator_id == user["user"]["id"]
    assert saved.description == data["description"]


def test_problem_creation_persists_ai_analysis_and_dynamic_profile_matches(client, db_session):
    user = register_user(client, "phase4@example.org")
    response = client.post(
        "/api/v1/problems",
        json={
            "title": "Community water monitoring",
            "description": "Residents need field research and community assessment for a water access issue.",
        },
        headers={"Authorization": f"Bearer {user['access_token']}"},
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["analysis"]["required_skills"]
    assert data["analysis"]["tags"]
    assert data["matches"]
    assert {"name", "role", "organization", "matching_skills", "score", "explanation"} <= set(data["matches"][0])

    problem_id = data["id"]
    assert db_session.query(AIAnalysis).filter_by(problem_id=problem_id).count() == 1
    assert db_session.query(Match).filter_by(problem_id=problem_id).count() == len(data["matches"])
    assert db_session.query(Profile).filter(Profile.user_id != user["user"]["id"]).count() >= 7

    matches = client.get(f"/api/v1/problems/{problem_id}/matches")
    assert matches.status_code == 200
    assert matches.json()["matches"] == data["matches"]


def test_matches_are_database_backed_and_change_with_ai_requirements(client, db_session, monkeypatch):
    from app import main as main_module

    class RequirementAwareAI:
        async def analyze_problem(self, description, image_name=None):
            if "road" in description.lower():
                return {
                    "summary": "Road infrastructure assessment",
                    "severity": "High",
                    "urgency": "Immediate",
                    "required_skills": ["Road engineering"],
                    "required_expertise": ["Public infrastructure"],
                    "required_resources": ["Civil inspection tools"],
                    "tags": ["roads"],
                }
            return {
                "summary": "Community AI monitoring",
                "severity": "Medium",
                "urgency": "Soon",
                "required_skills": ["Machine learning"],
                "required_expertise": ["Artificial intelligence"],
                "required_resources": ["AI lab"],
                "tags": ["software"],
            }

    monkeypatch.setattr(main_module, "ai_service", RequirementAwareAI())
    user = register_user(client, "dynamic-matches@example.org")
    headers = {"Authorization": f"Bearer {user['access_token']}"}

    road = client.post(
        "/api/v1/problems",
        json={"title": "Road hazard", "description": "A road engineering assessment is needed."},
        headers=headers,
    ).json()
    software = client.post(
        "/api/v1/problems",
        json={"title": "AI monitor", "description": "A machine learning monitor is needed."},
        headers=headers,
    ).json()

    road_matches = client.get(f"/api/v1/problems/{road['id']}/matches")
    software_matches = client.get(f"/api/v1/problems/{software['id']}/matches")
    assert road_matches.status_code == 200
    assert software_matches.status_code == 200
    assert road_matches.json()["matches"]
    assert software_matches.json()["matches"]
    assert road_matches.json()["matches"][0]["candidate_id"] != software_matches.json()["matches"][0]["candidate_id"]

    profile_user_ids = {user_id for (user_id,) in db_session.query(Profile.user_id).all()}
    for result in [road_matches.json(), software_matches.json()]:
        for match in result["matches"]:
            assert match["candidate_id"] in profile_user_ids
            assert 0 < match["score"] <= 100
            assert match["matching_skills"]
            assert "profile_id" not in match


def test_matches_for_real_problem_are_available_without_frontend_user_id(client):
    user = register_user(client, "matches-public@example.org")
    problem = client.post(
        "/api/v1/problems",
        json={"title": "Water issue", "description": "Residents need water quality research."},
        headers={"Authorization": f"Bearer {user['access_token']}"},
    ).json()

    response = client.get(f"/api/v1/problems/{problem['id']}/matches")
    assert response.status_code == 200
    assert response.json()["problem_id"] == problem["id"]


def test_unauthenticated_problem_creation_rejected(client):
    response = client.post(
        "/api/v1/problems",
        json={
            "title": "No auth",
            "description": "this should fail",
            "latitude": 12.0,
            "longitude": 77.0,
        },
    )
    assert response.status_code == 401


def test_problem_list_reads_database_records(client):
    user = register_user(client, "listuser@example.org")
    token = user["access_token"]

    first = client.post(
        "/api/v1/problems",
        json={
            "title": "First problem",
            "description": "Alpha issue",
            "latitude": 20.0,
            "longitude": 78.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    second = client.post(
        "/api/v1/problems",
        json={
            "title": "Second problem",
            "description": "Beta issue",
            "latitude": 21.0,
            "longitude": 79.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get("/api/v1/problems")
    assert response.status_code == 200
    data = response.json()
    ids = {item["id"] for item in data["items"]}
    assert first.json()["id"] in ids
    assert second.json()["id"] in ids


def test_problem_detail_and_404(client):
    user = register_user(client, "detailuser@example.org")
    token = user["access_token"]

    created = client.post(
        "/api/v1/problems",
        json={
            "title": "Broken lights",
            "description": "Streetlights are out on the road.",
            "latitude": 22.0,
            "longitude": 88.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    problem_id = created.json()["id"]

    response = client.get(f"/api/v1/problems/{problem_id}")
    assert response.status_code == 200
    assert response.json()["id"] == problem_id

    missing = client.get("/api/v1/problems/does-not-exist")
    assert missing.status_code == 404


def test_my_reports_returns_only_current_users_reports(client):
    user_a = register_user(client, "usera@example.org", name="User A")
    user_b = register_user(client, "userb@example.org", name="User B")

    a_token = user_a["access_token"]
    b_token = user_b["access_token"]

    client.post(
        "/api/v1/problems",
        json={
            "title": "A issue",
            "description": "User A problem",
            "latitude": 10.0,
            "longitude": 70.0,
        },
        headers={"Authorization": f"Bearer {a_token}"},
    )
    client.post(
        "/api/v1/problems",
        json={
            "title": "B issue",
            "description": "User B problem",
            "latitude": 11.0,
            "longitude": 71.0,
        },
        headers={"Authorization": f"Bearer {b_token}"},
    )

    response = client.get("/api/v1/problems/me", headers={"Authorization": f"Bearer {a_token}"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["creator_id"] == user_a["user"]["id"] for item in items)
    assert len(items) == 1


def test_support_requires_auth_and_is_unique(client):
    user = register_user(client, "supporter@example.org")
    token = user["access_token"]
    problem = client.post(
        "/api/v1/problems",
        json={
            "title": "Support me",
            "description": "Need support for a blocked culvert.",
            "latitude": 19.0,
            "longitude": 72.0,
        },
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    unauth = client.post(f"/api/v1/problems/{problem['id']}/support")
    assert unauth.status_code == 401

    first = client.post(
        f"/api/v1/problems/{problem['id']}/support",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 201, first.text
    assert first.json()["support_count"] == 1

    second = client.post(
        f"/api/v1/problems/{problem['id']}/support",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 409

    record = client.get(f"/api/v1/problems/{problem['id']}/support", headers={"Authorization": f"Bearer {token}"})
    assert record.status_code == 200
    assert record.json()["has_supported"] is True
    assert record.json()["support_count"] == 1


def test_multiple_users_can_support_same_problem(client):
    user_a = register_user(client, "supporta@example.org")
    user_b = register_user(client, "supportb@example.org")

    problem = client.post(
        "/api/v1/problems",
        json={
            "title": "Community sink",
            "description": "Rainwater pooling on the common path.",
            "latitude": 30.0,
            "longitude": 76.0,
        },
        headers={"Authorization": f"Bearer {user_a['access_token']}"},
    ).json()

    first = client.post(
        f"/api/v1/problems/{problem['id']}/support",
        headers={"Authorization": f"Bearer {user_a['access_token']}"},
    )
    second = client.post(
        f"/api/v1/problems/{problem['id']}/support",
        headers={"Authorization": f"Bearer {user_b['access_token']}"},
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(f"/api/v1/problems/{problem['id']}/support", headers={"Authorization": f"Bearer {user_a['access_token']}"})
    assert response.status_code == 200
    assert response.json()["support_count"] == 2


def test_invalid_coordinates_and_input_rejected(client):
    user = register_user(client, "invalid@example.org")
    token = user["access_token"]

    bad_coords = client.post(
        "/api/v1/problems",
        json={
            "title": "bad coords",
            "description": "This is fine",
            "latitude": 100,
            "longitude": 10,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad_coords.status_code == 400

    bad_desc = client.post(
        "/api/v1/problems",
        json={
            "title": "bad desc",
            "description": "",
            "latitude": 12,
            "longitude": 77,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad_desc.status_code == 400


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "X", "description": "valid description", "latitude": -91, "longitude": 0},
        {"title": "X", "description": "valid description", "latitude": 0, "longitude": 181},
    ],
)
def test_coordinate_bounds_are_validated(client, payload):
    user = register_user(client, "bounds@example.org")
    token = user["access_token"]
    response = client.post(
        "/api/v1/problems",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
