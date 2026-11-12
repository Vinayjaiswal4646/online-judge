PROBLEM = {
    "title": "Two Sum",
    "description": "Print the sum of two integers.",
    "difficulty": "easy",
    "test_cases": [
        {"input_data": "1 2", "expected_output": "3", "is_sample": True},
        {"input_data": "5 7", "expected_output": "12", "is_sample": False},
    ],
}


def test_signup_login_me(client):
    r = client.post("/auth/signup", json={"username": "vinay", "password": "password123"})
    assert r.status_code == 201
    assert client.post(
        "/auth/signup", json={"username": "vinay", "password": "password123"}
    ).status_code == 409

    bad = client.post("/auth/login", data={"username": "vinay", "password": "wrongpass"})
    assert bad.status_code == 401

    token = client.post(
        "/auth/login", data={"username": "vinay", "password": "password123"}
    ).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["username"] == "vinay"


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_only_admin_can_create_problem(client, admin_headers):
    client.post("/auth/signup", json={"username": "user1", "password": "password123"})
    token = client.post(
        "/auth/login", data={"username": "user1", "password": "password123"}
    ).json()["access_token"]
    r = client.post("/problems", json=PROBLEM, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert client.post("/problems", json=PROBLEM, headers=admin_headers).status_code == 201


def test_hidden_test_cases_not_exposed(client, admin_headers):
    client.post("/problems", json=PROBLEM, headers=admin_headers)
    detail = client.get("/problems/two-sum").json()
    assert len(detail["samples"]) == 1
    assert detail["samples"][0]["expected_output"] == "3"


def test_list_and_duplicate(client, admin_headers):
    client.post("/problems", json=PROBLEM, headers=admin_headers)
    assert client.post("/problems", json=PROBLEM, headers=admin_headers).status_code == 409
    assert len(client.get("/problems").json()) == 1
    assert client.get("/problems?difficulty=hard").json() == []
    assert client.get("/problems/nope").status_code == 404
