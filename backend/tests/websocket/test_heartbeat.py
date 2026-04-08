from conftest import heartbeat_message, hello_message, login, provision_node


def test_heartbeat_updates_node_state(client):
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
        websocket.receive_json()
        websocket.send_json(heartbeat_message(provisioned["id"], status="ready"))

        node_response = client.get(f"/api/nodes/{provisioned['id']}")
        assert node_response.status_code == 200
        assert node_response.json()["operationalState"] == "ready"
