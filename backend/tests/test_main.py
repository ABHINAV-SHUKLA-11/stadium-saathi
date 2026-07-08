import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_crowd_densities():
    response = client.get("/api/crowd")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "zone_id" in data[0]
    assert "density" in data[0]
    assert "status" in data[0]

def test_login_dashboard_incorrect():
    response = client.post("/api/dashboard/login", json={"password": "wrong_password"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False

def test_login_dashboard_correct():
    response = client.post("/api/dashboard/login", json={"password": "stadium_saathi_admin_2026"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["token"] == "stadium_saathi_admin_2026"
