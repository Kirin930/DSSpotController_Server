from conftest import login


def test_healthcheck(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_and_me(client):
    login(client)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "admin"
