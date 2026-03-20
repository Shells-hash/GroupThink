def test_register(client):
    res = client.post("/auth/register", json={
        "username": "alice", "email": "alice@test.com", "password": "secret"
    })
    assert res.status_code == 201
    assert "access_token" in res.json()


def test_register_duplicate_username(client):
    client.post("/auth/register", json={"username": "alice", "email": "a@test.com", "password": "x"})
    res = client.post("/auth/register", json={"username": "alice", "email": "b@test.com", "password": "x"})
    assert res.status_code == 409


def test_login(client):
    client.post("/auth/register", json={"username": "bob", "email": "bob@test.com", "password": "pw"})
    res = client.post("/auth/login", json={"username": "bob", "password": "pw"})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password(client):
    client.post("/auth/register", json={"username": "bob", "email": "bob@test.com", "password": "pw"})
    res = client.post("/auth/login", json={"username": "bob", "password": "wrong"})
    assert res.status_code == 401


def test_me(client, auth_headers):
    res = client.get("/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["username"] == "testuser"


def test_me_unauthenticated(client):
    res = client.get("/auth/me")
    assert res.status_code == 403
