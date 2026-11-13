import subprocess

import pytest

from app import runner
from app.config import settings
from app.runner import RunResult, SandboxError, build_docker_command


# ---------------------------------------------------------------------------
# Part 1: tests that need NO Docker (Docker is faked). They run everywhere.
# ---------------------------------------------------------------------------

def test_docker_command_has_all_safety_flags():
    cmd = build_docker_command("judge-test", "/tmp/x", 2000, 128)
    joined = " ".join(cmd)
    assert "--network none" in joined
    assert "--memory 128m" in joined
    assert "--memory-swap 128m" in joined
    assert "--read-only" in cmd
    assert "--cap-drop ALL" in joined
    assert "no-new-privileges" in joined
    assert "--user 65534:65534" in joined
    assert "--pids-limit 64" in joined
    assert "/tmp/x:/sandbox:ro" in joined
    assert "timeout -k 1 2.000 python" in joined


def fake_docker(monkeypatch, run_rc=0, stdout="", stderr="", oom=False):
    """Replace subprocess.run so no real Docker is needed."""

    def fake_run(cmd, **kwargs):
        action = cmd[1]
        if action == "run":
            return subprocess.CompletedProcess(cmd, run_rc, stdout, stderr)
        if action == "inspect":
            return subprocess.CompletedProcess(cmd, 0, "true\n" if oom else "false\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")  # docker rm

    monkeypatch.setattr(settings, "sandbox_backend", "docker")
    monkeypatch.setattr(runner.subprocess, "run", fake_run)


def run(code="print(1)"):
    return runner.run_python(code, "", 1000, 128)


def test_ok(monkeypatch):
    fake_docker(monkeypatch, run_rc=0, stdout="3\n")
    result = run()
    assert result.status == "ok" and result.stdout == "3\n"


def test_exit_124_is_time_limit(monkeypatch):
    fake_docker(monkeypatch, run_rc=124)
    assert run().status == "time_limit_exceeded"


def test_exit_137_with_oom_is_memory_limit(monkeypatch):
    fake_docker(monkeypatch, run_rc=137, oom=True)
    assert run().status == "memory_limit_exceeded"


def test_exit_137_without_oom_is_time_limit(monkeypatch):
    fake_docker(monkeypatch, run_rc=137, oom=False)
    assert run().status == "time_limit_exceeded"


def test_exit_1_is_runtime_error(monkeypatch):
    fake_docker(monkeypatch, run_rc=1, stderr="ZeroDivisionError")
    assert run().status == "runtime_error"


def test_docker_not_running_is_sandbox_error(monkeypatch):
    fake_docker(
        monkeypatch, run_rc=1,
        stderr="failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine",
    )
    with pytest.raises(SandboxError):
        run()


def test_exit_125_is_sandbox_error(monkeypatch):
    fake_docker(monkeypatch, run_rc=125, stderr="docker: invalid flag")
    with pytest.raises(SandboxError):
        run()


def test_sandbox_failure_gives_internal_error_verdict(client, admin_headers, monkeypatch):
    problem = {
        "title": "Echo", "description": "x", "difficulty": "easy",
        "test_cases": [{"input_data": "1\n", "expected_output": "1", "is_sample": True}],
    }
    client.post("/problems", json=problem, headers=admin_headers)
    fake_docker(monkeypatch, run_rc=125, stderr="docker broke")
    r = client.post(
        "/submissions",
        json={"problem_slug": "echo", "code": "print(1)"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    assert r.json()["verdict"] == "internal_error"


# ---------------------------------------------------------------------------
# Part 2: REAL Docker tests. Skipped automatically if Docker isn't ready.
# Before running: docker pull python:3.12-slim
# ---------------------------------------------------------------------------

def docker_ready() -> bool:
    try:
        ok = subprocess.run(["docker", "info"], capture_output=True, timeout=20).returncode == 0
        img = subprocess.run(
            ["docker", "image", "inspect", settings.sandbox_image],
            capture_output=True, timeout=20,
        ).returncode == 0
        return ok and img
    except Exception:
        return False


needs_docker = pytest.mark.skipif(
    not docker_ready(), reason="Docker not running or python:3.12-slim not pulled"
)


@pytest.fixture()
def real_docker(monkeypatch):
    monkeypatch.setattr(settings, "sandbox_backend", "docker")


@needs_docker
def test_real_ok_and_input(real_docker):
    r = runner.run_python("print(int(input()) * 2)", "21\n", 5000, 128)
    assert r.status == "ok" and r.stdout.strip() == "42"


@needs_docker
def test_real_time_limit(real_docker):
    r = runner.run_python("while True:\n    pass\n", "", 1000, 128)
    assert r.status == "time_limit_exceeded"


@needs_docker
def test_real_memory_limit(real_docker):
    r = runner.run_python("x = bytearray(500 * 1024 * 1024)\nprint(len(x))\n", "", 5000, 64)
    assert r.status == "memory_limit_exceeded"


@needs_docker
def test_real_network_is_blocked(real_docker):
    code = "import socket\nsocket.create_connection(('1.1.1.1', 80), timeout=3)\nprint('connected')\n"
    r = runner.run_python(code, "", 8000, 128)
    assert r.status == "runtime_error"


@needs_docker
def test_real_filesystem_is_read_only(real_docker):
    code = "open('/sandbox/hacked.txt', 'w').write('x')\nprint('written')\n"
    r = runner.run_python(code, "", 5000, 128)
    assert r.status == "runtime_error"


@needs_docker
def test_real_cannot_see_host_files(real_docker):
    code = "import os\nprint(os.path.exists('/Users') or os.path.exists('C:/'))\n"
    r = runner.run_python(code, "", 5000, 128)
    assert r.status == "ok" and r.stdout.strip() == "False"
