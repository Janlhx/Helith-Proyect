import json
from unittest.mock import patch

import pytest

from core.config import settings
from main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_ping_endpoint(client):
    """Test that the /ping endpoint returns pong and 200 OK."""
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.data.decode("utf-8") == "pong"

def test_index_endpoint(client):
    """Test that the index endpoint returns the application name and status."""
    response = client.get("/")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["name"] == "Helith"
    assert data["status"] == "running"

def test_health_endpoint(client):
    """Test that the /health endpoint displays bot status and configuration."""
    with patch("main.bot") as mock_bot:
        mock_bot.is_ready.return_value = True
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"
        assert data["bot"] is True
        assert "version" in data
        assert "tavily" in data

def test_api_metrics_unauthorized(client):
    """Test that /api/metrics rejects unauthorized requests."""
    response = client.get("/api/metrics")
    assert response.status_code == 401

def test_api_metrics_authorized_via_session(client):
    """Test that /api/metrics succeeds when authorized via session."""
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        
    with patch("domains.monitoring.service.monitoring_service") as mock_monitoring:
        mock_monitoring.get_full_report.return_value = {
            "status": "ok",
            "active_alerts": 0,
        }
        response = client.get("/api/metrics")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"
        assert data["active_alerts"] == 0

def test_api_metrics_authorized_via_header(client):
    """Test that /api/metrics succeeds when authorized via Bearer token."""
    with patch("domains.monitoring.service.monitoring_service") as mock_monitoring:
        mock_monitoring.get_full_report.return_value = {
            "status": "ok",
            "active_alerts": 0,
        }
        
        # Token prefix matching settings.DISCORD_TOKEN[:20]
        fake_token = (
            settings.DISCORD_TOKEN[:20]
            if settings.DISCORD_TOKEN
            else "fake_token_value_longer_than_20"
        )
        headers = {"Authorization": f"Bearer {fake_token}"}
        
        response = client.get("/api/metrics", headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"
