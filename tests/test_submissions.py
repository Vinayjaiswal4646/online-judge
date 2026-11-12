import pytest

PROBLEM = {
    "title": "Add Two Numbers",
    "description": "Print the sum of two integers.",
    "difficulty": "easy",
    "time_limit_ms": 500,
    "test_cases": [
        {"input_data": "1 2\n", "expected_output": "3", "is_sample": True},
        {"input_data": "10 25\n", "expected_output": "35", "is_sample": False},
    ],
}

GOOD = "a, b = map(int, input().split())\nprint(a + b)\n"


@pytest.fixture()
def problem(client, admin_headers):
    client.post("/problems", json=PROBLEM, headers=admin_headers)
    return "add-two-numbers"


def submit(client, headers, slug, code, **extra):
    return client.post(
        "/submissions",
        json={"problem_slug": slug, "code": code, **extra},
        headers=headers,
    )


def test_accepted(client, admin_headers, problem):
    r = submit(client, admin_headers, problem, GOOD)
    assert r.status_code == 201
    assert r.json()["verdict"] == "accepted"
    assert r.json()["runtime_ms"] is not None


def test_wrong_answer(client, admin_headers, problem):
    code = "a, b = map(int, input().split())\nprint(a - b)\n"
    assert submit(client, admin_headers, problem, code).json()["verdict"] == "wrong_answer"


def test_fails_on_hidden_case_only(client, admin_headers, problem):
    code = "a, b = map(int, input().split())\nprint(3 if a == 1 else 0)\n"
    assert submit(client, admin_headers, problem, code).json()["verdict"] == "wrong_answer"


def test_runtime_error(client, admin_headers, problem):
    r = submit(client, admin_headers, problem, "print(1 // 0)\n")
    assert r.json()["verdict"] == "runtime_error"


def test_syntax_error_is_runtime_error(client, admin_headers, problem):
    r = submit(client, admin_headers, problem, "print(((\n")
    assert r.json()["verdict"] == "runtime_error"


def test_time_limit_exceeded(client, admin_headers, problem):
    r = submit(client, admin_headers, problem, "while True:\n    pass\n")
    assert r.json()["verdict"] == "time_limit_exceeded"


def test_trailing_whitespace_is_ignored(client, admin_headers, problem):
    code = "a, b = map(int, input().split())\nprint(a + b, end='   \\n\\n')\n"
    assert submit(client, admin_headers, problem, code).json()["verdict"] == "accepted"


def test_requires_login(client, problem):
    r = client.post("/submissions", json={"problem_slug": problem, "code": GOOD})
    assert r.status_code == 401


def test_unknown_problem_and_language(client, admin_headers, problem):
    assert submit(client, admin_headers, "nope", GOOD).status_code == 404
    assert submit(client, admin_headers, problem, GOOD, language="cobol").status_code == 400


def test_history_and_privacy(client, admin_headers, problem):
    sub_id = submit(client, admin_headers, problem, GOOD).json()["id"]
    assert len(client.get("/submissions", headers=admin_headers).json()) == 1
    assert client.get(f"/submissions/{sub_id}", headers=admin_headers).status_code == 200

    client.post("/auth/signup", json={"username": "other", "password": "password123"})
    token = client.post(
        "/auth/login", data={"username": "other", "password": "password123"}
    ).json()["access_token"]
    other = {"Authorization": f"Bearer {token}"}
    assert client.get(f"/submissions/{sub_id}", headers=other).status_code == 404
    assert client.get("/submissions", headers=other).json() == []
