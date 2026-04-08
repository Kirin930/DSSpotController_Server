from urllib.parse import parse_qs, urlparse

from conftest import hello_message, login, provision_node, upload_spot


def test_connecting_node_receives_signed_sync_urls(client):
    login(client)
    provisioned = provision_node(client)
    upload_spot(client)

    with client.websocket_connect("/ws/nodes") as websocket:
        websocket.send_json(
            hello_message(
                provisioned["id"],
                provisioned["authToken"],
                provisioned["displayName"],
            )
        )
        websocket.receive_json()
        sync_required = websocket.receive_json()

        assert sync_required["type"] == "SYNC_REQUIRED"
        download_url = sync_required["payload"]["spots"][0]["downloadUrl"]
        parsed = urlparse(download_url)
        query = parse_qs(parsed.query)

        assert parsed.path.endswith("/api/spots/" + sync_required["payload"]["spots"][0]["spotId"] + "/download")
        assert query["nodeId"] == [provisioned["id"]]
        assert "signature" in query
