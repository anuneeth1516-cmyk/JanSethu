import io
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(name="client")
def client_fixture():
    return TestClient(app)


def test_upload_image_success(client):
    file_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    response = client.post(
        "/api/v1/upload",
        files={"file": ("test.png", io.BytesIO(file_bytes), "image/png")},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["url"].startswith("/uploads/")
    assert data["media_type"] == "image"
    assert data["filename"].endswith(".png")

    # Verify static file is retrievable
    get_res = client.get(data["url"])
    assert get_res.status_code == 200
    assert get_res.content == file_bytes


def test_upload_video_success(client):
    video_bytes = b"fake-mp4-content"
    response = client.post(
        "/api/v1/upload",
        files={"file": ("evidence.mp4", io.BytesIO(video_bytes), "video/mp4")},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["url"].startswith("/uploads/")
    assert data["media_type"] == "video"
    assert data["filename"].endswith(".mp4")


def test_upload_invalid_type_rejected(client):
    response = client.post(
        "/api/v1/upload",
        files={"file": ("script.exe", io.BytesIO(b"binary"), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]
