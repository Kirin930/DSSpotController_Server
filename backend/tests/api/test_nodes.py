from conftest import approve_enrollment, login, provision_node, request_enrollment


def test_node_provision_and_toggle(client):
    login(client)
    provisioned = provision_node(client)

    nodes_response = client.get("/api/nodes")
    assert nodes_response.status_code == 200
    assert nodes_response.json()[0]["id"] == provisioned["id"]

    disable_response = client.patch(
        f"/api/nodes/{provisioned['id']}/enabled", json={"enabled": False}
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False

    autoplay_response = client.patch(
        f"/api/nodes/{provisioned['id']}/autoplay",
        json={"autoplaySelected": False},
    )
    assert autoplay_response.status_code == 200
    assert autoplay_response.json()["autoplaySelected"] is False


def test_enrollment_request_approve_and_status(client):
    login(client)
    enrollment = request_enrollment(client, node_id="node-xyz", display_name="Back Room")

    list_response = client.get("/api/nodes/enrollments?status=pending")
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == enrollment["id"]

    approved = approve_enrollment(client, enrollment["id"])
    assert approved["status"] == "approved"

    status_response = client.get(
        f"/api/nodes/enrollments/{enrollment['id']}/status",
        params={"pairing_code": enrollment["pairingCode"]},
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "approved"
    assert status_response.json()["authToken"]


def test_csrf_required_for_state_changes(client):
    login(client)
    client.headers.pop("X-CSRF-Token", None)

    response = client.post(
        "/api/nodes/provision",
        json={
            "nodeId": "node-missing-csrf",
            "displayName": "No CSRF",
            "enabled": True,
            "autoplaySelected": True,
        },
    )
    assert response.status_code == 403
