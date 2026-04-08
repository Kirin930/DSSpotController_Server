from conftest import login, upload_spot


def test_scheduler_config_round_trip(client):
    login(client)
    spot = upload_spot(client)

    update_response = client.put(
        "/api/scheduler",
        json={
            "enabled": False,
            "intervalMinutes": 5,
            "spotSequence": [spot["id"]],
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["spotSequence"] == [spot["id"]]
    assert update_response.json()["revision"] == 1

    start_response = client.post("/api/scheduler/start")
    assert start_response.status_code == 200
    assert start_response.json()["message"] == "Autoplay started"

    get_response = client.get("/api/scheduler")
    assert get_response.status_code == 200
    assert get_response.json()["enabled"] is True

    stop_response = client.post("/api/scheduler/stop")
    assert stop_response.status_code == 200
    assert stop_response.json()["message"] == "Autoplay stopped"
