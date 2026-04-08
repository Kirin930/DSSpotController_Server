import threading

from conftest import (
    hello_message,
    login,
    playback_started_message,
    provision_node,
    upload_spot,
)


def test_play_endpoint_waits_for_node_ack(client):
    login(client)
    provisioned = provision_node(client)
    spot = upload_spot(client)

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

        sync_message = websocket.receive_json()
        assert sync_message["type"] == "SYNC_REQUIRED"

        response_holder = {}

        def invoke_play():
            response_holder["response"] = client.post(
                "/api/playback/play",
                json={
                    "spotId": spot["id"],
                    "nodeIds": [provisioned["id"]],
                    "replaceIfPlaying": True,
                },
            )

        thread = threading.Thread(target=invoke_play)
        thread.start()

        play_message = websocket.receive_json()
        assert play_message["type"] == "PLAY"
        websocket.send_json(
            playback_started_message(
                provisioned["id"],
                spot["id"],
                play_message["requestId"],
            )
        )

        thread.join(timeout=5)
        response = response_holder["response"]
        assert response.status_code == 200
        assert response.json()["results"][0]["status"] == "started"
