from conftest import (
    approve_enrollment,
    hello_message,
    login,
    provision_node,
    request_enrollment,
)


def test_hello_marks_node_online(client):
    login(client)
    provisioned = provision_node(client)

    with client.websocket_connect("/ws/nodes") as websocket:
        websocket.send_json(
            hello_message(
                provisioned["id"],
                provisioned["authToken"],
                provisioned["displayName"],
            )
        )
        register_ack = websocket.receive_json()
        assert register_ack["type"] == "REGISTER_ACK"
        assert register_ack["payload"]["nodeId"] == provisioned["id"]

        node_response = client.get(f"/api/nodes/{provisioned['id']}")
        assert node_response.status_code == 200
        assert node_response.json()["connectionState"] == "online"


def test_hello_accepts_same_major_with_minor_version(client):
    login(client)
    provisioned = provision_node(client, node_id="node-002", display_name="Speaker B")

    with client.websocket_connect("/ws/nodes") as websocket:
        websocket.send_json(
            hello_message(
                provisioned["id"],
                provisioned["authToken"],
                provisioned["displayName"],
                protocol_version="1.1",
            )
        )
        register_ack = websocket.receive_json()
        assert register_ack["type"] == "REGISTER_ACK"


def test_approved_enrollment_can_complete_hello(client):
    login(client)
    enrollment = request_enrollment(client, node_id="node-enroll", display_name="Lobby")
    approve_enrollment(client, enrollment["id"])
    status_response = client.get(
        f"/api/nodes/enrollments/{enrollment['id']}/status",
        params={"pairing_code": enrollment["pairingCode"]},
    )
    auth_token = status_response.json()["authToken"]

    with client.websocket_connect("/ws/nodes") as websocket:
        websocket.send_json(
            hello_message("node-enroll", auth_token, "Lobby", protocol_version="1.0")
        )
        register_ack = websocket.receive_json()
        assert register_ack["type"] == "REGISTER_ACK"
