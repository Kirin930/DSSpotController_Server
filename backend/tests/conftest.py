from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path):
    settings = Settings.from_env(repo_root=Path(__file__).resolve().parents[2])
    settings.database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    settings.storage_root = tmp_path / "storage"
    settings.public_base_url = "http://testserver"
    settings.default_admin_username = "admin"
    settings.default_admin_password = "admin123!"
    settings.command_ack_timeout_seconds = 2
    settings.heartbeat_sweep_interval_seconds = 1
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123!"},
    )
    assert response.status_code == 200
    csrf_token = response.json()["csrfToken"]
    client.headers.update({"X-CSRF-Token": csrf_token})


def provision_node(
    client: TestClient, node_id: str = "node-001", display_name: str = "Speaker A"
) -> dict:
    response = client.post(
        "/api/nodes/provision",
        json={
            "nodeId": node_id,
            "displayName": display_name,
            "enabled": True,
            "autoplaySelected": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def upload_spot(client: TestClient, title: str = "Spring Promo") -> dict:
    response = client.post(
        "/api/spots",
        data={"title": title},
        files={"file": ("spring.mp3", b"fake-audio-data", "audio/mpeg")},
    )
    assert response.status_code == 200
    return response.json()


def request_enrollment(
    client: TestClient,
    node_id: str = "node-001",
    display_name: str = "Speaker A",
) -> dict:
    response = client.post(
        "/api/nodes/enrollments/request",
        json={
            "nodeId": node_id,
            "displayName": display_name,
            "platform": "android",
            "appVersion": "1.0.0",
            "deviceModel": "Test Device",
        },
    )
    assert response.status_code == 200
    return response.json()


def approve_enrollment(client: TestClient, enrollment_id: str) -> dict:
    response = client.post(
        f"/api/nodes/enrollments/{enrollment_id}/approve",
        json={"enabled": True, "autoplaySelected": True},
    )
    assert response.status_code == 200
    return response.json()


def hello_message(
    node_id: str,
    auth_token: str,
    display_name: str,
    protocol_version: int | str = 1,
) -> dict:
    return {
        "type": "HELLO",
        "protocolVersion": protocol_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "nodeId": node_id,
            "authToken": auth_token,
            "displayName": display_name,
            "platform": "android",
            "appVersion": "1.0.0",
            "deviceModel": "Test Device",
        },
    }


def playback_started_message(node_id: str, spot_id: str, request_id: str) -> dict:
    return {
        "type": "PLAYBACK_STARTED",
        "protocolVersion": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "requestId": request_id,
        "payload": {"nodeId": node_id, "spotId": spot_id},
    }


def heartbeat_message(node_id: str, status: str = "ready") -> dict:
    return {
        "type": "HEARTBEAT",
        "protocolVersion": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {"nodeId": node_id, "status": status, "currentSpotId": None},
    }
