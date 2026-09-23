import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "system" in data
    assert data["status"] == "online"


def test_health_check_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "github" in data
    assert "version" in data
    assert data["service"] == settings.PROJECT_NAME


def test_list_projects_endpoint():
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_active_project_empty():
    # If no repo connected yet, returns 200 with null
    response = client.get("/api/v1/projects/active")
    assert response.status_code == 200
