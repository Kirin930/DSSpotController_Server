from conftest import login, upload_spot


def test_spot_upload_and_list(client):
    login(client)
    spot = upload_spot(client)

    list_response = client.get("/api/spots")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == spot["id"]

    patch_response = client.patch(
        f"/api/spots/{spot['id']}",
        json={"title": "Updated Promo", "active": False},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Updated Promo"
    assert patch_response.json()["active"] is False
