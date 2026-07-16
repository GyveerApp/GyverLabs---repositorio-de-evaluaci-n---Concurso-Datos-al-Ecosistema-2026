from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_credenciales_invalidas():
    response = client.post("/auth/login", json={"email": "no-existe@x.co", "password": "x"})
    assert response.status_code == 401
