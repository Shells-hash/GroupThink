def test_create_group(client, auth_headers):
    res = client.post("/groups", json={"name": "Trip Planning"}, headers=auth_headers)
    assert res.status_code == 201
    assert res.json()["name"] == "Trip Planning"


def test_list_groups(client, auth_headers):
    client.post("/groups", json={"name": "G1"}, headers=auth_headers)
    client.post("/groups", json={"name": "G2"}, headers=auth_headers)
    res = client.get("/groups", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_get_group_detail(client, auth_headers):
    group_id = client.post("/groups", json={"name": "G"}, headers=auth_headers).json()["id"]
    res = client.get(f"/groups/{group_id}", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()["members"]) == 1


def test_invite_member(client, auth_headers, db):
    from backend.services.auth_service import register_user
    register_user(db, "friend", "friend@test.com", "pw")

    group_id = client.post("/groups", json={"name": "G"}, headers=auth_headers).json()["id"]
    res = client.post(f"/groups/{group_id}/invite", json={"username": "friend"}, headers=auth_headers)
    assert res.status_code == 201

    detail = client.get(f"/groups/{group_id}", headers=auth_headers).json()
    assert len(detail["members"]) == 2


def test_invite_nonexistent_user(client, auth_headers):
    group_id = client.post("/groups", json={"name": "G"}, headers=auth_headers).json()["id"]
    res = client.post(f"/groups/{group_id}/invite", json={"username": "ghost"}, headers=auth_headers)
    assert res.status_code == 404


def test_delete_group(client, auth_headers):
    group_id = client.post("/groups", json={"name": "G"}, headers=auth_headers).json()["id"]
    res = client.delete(f"/groups/{group_id}", headers=auth_headers)
    assert res.status_code == 204
