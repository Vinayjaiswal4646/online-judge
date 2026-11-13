"""Runs a user's Python code against one input and reports what happened.

Two backends, chosen with SANDBOX_BACKEND in .env:
  docker : every run happens in a throwaway, locked-down container (SAFE)
  local  : runs directly on your machine with only a timeout (NOT safe)
"""
import logging
import os
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass

from .config import settings

log = logging.getLogger("judge")

MAX_OUTPUT_CHARS = 100_000
# Extra wall-clock time allowed for the container to start up. The real time
# limit is enforced INSIDE the container by `timeout`.
STARTUP_GRACE_S = 20

DOCKER_ERROR_MARKERS = (
    "cannot connect to the docker daemon",
    "failed to connect to the docker api",
    "unable to find image",
    "error response from daemon",
)


class SandboxError(Exception):
    """The sandbox itself failed (Docker not running, image missing, ...).
    This is our problem, not the user's code."""


@dataclass
class RunResult:
    # "ok", "runtime_error", "time_limit_exceeded", "memory_limit_exceeded"
    status: str
    stdout: str = ""
    stderr: str = ""
    runtime_ms: int = 0


def run_python(code: str, input_data: str, time_limit_ms: int, memory_mb: int = 256) -> RunResult:
    if settings.sandbox_backend == "docker":
        return _run_docker(code, input_data, time_limit_ms, memory_mb)
    return _run_local(code, input_data, time_limit_ms)


# ---------------------------------------------------------------- docker ---

def build_docker_command(name: str, host_dir: str, time_limit_ms: int, memory_mb: int) -> list[str]:
    seconds = f"{time_limit_ms / 1000:.3f}"
    return [
        "docker", "run",
        "--name", name,
        "-i",                                  # let us send test input on stdin
        "--network", "none",                   # no internet, no local network
        "--memory", f"{memory_mb}m",           # hard RAM cap
        "--memory-swap", f"{memory_mb}m",      # no swap, so the cap is real
        "--cpus", "1",                         # at most one CPU core
        "--pids-limit", "64",                  # stops fork bombs
        "--read-only",                         # container filesystem is read-only
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",  # tiny scratch space only
        "--cap-drop", "ALL",                   # no special Linux privileges
        "--security-opt", "no-new-privileges",
        "--user", "65534:65534",               # run as "nobody", not root
        "-v", f"{host_dir}:/sandbox:ro",       # user's code, mounted read-only
        "-w", "/tmp",
        settings.sandbox_image,
        # `timeout` enforces the real time limit inside the container.
        # -k 1: if the program ignores the polite stop, kill it 1s later.
        "timeout", "-k", "1", seconds,
        "python", "-I", "-B", "/sandbox/solution.py",
    ]


def _run_docker(code: str, input_data: str, time_limit_ms: int, memory_mb: int) -> RunResult:
    name = f"judge-{uuid.uuid4().hex[:12]}"
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        with open(os.path.join(tmp, "solution.py"), "w", encoding="utf-8") as f:
            f.write(code)

        cmd = build_docker_command(name, tmp, time_limit_ms, memory_mb)
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=time_limit_ms / 1000 + STARTUP_GRACE_S,
            )
        except subprocess.TimeoutExpired:
            _remove_container(name)
            return RunResult("time_limit_exceeded", runtime_ms=time_limit_ms)
        except FileNotFoundError:
            raise SandboxError("The 'docker' command was not found")

        elapsed = int((time.perf_counter() - start) * 1000)
        oom = _was_oom_killed(name)
        _remove_container(name)

    rc = proc.returncode
    stderr = proc.stderr[-2000:]

    if rc == 125 or (rc != 0 and any(m in stderr.lower() for m in DOCKER_ERROR_MARKERS)):
        raise SandboxError(stderr.strip()[-500:] or "docker failed to start the container")
    if rc in (126, 127):
        raise SandboxError(f"Container could not run the program (exit {rc}): {stderr.strip()[-300:]}")
    if oom:
        return RunResult("memory_limit_exceeded", runtime_ms=elapsed)
    if rc in (124, 137):  # 124 = `timeout` fired, 137 = it had to be killed
        return RunResult("time_limit_exceeded", runtime_ms=time_limit_ms)
    if rc != 0:
        return RunResult("runtime_error", proc.stdout, stderr, elapsed)
    return RunResult("ok", proc.stdout[:MAX_OUTPUT_CHARS], stderr, elapsed)


def _was_oom_killed(name: str) -> bool:
    try:
        out = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.OOMKilled}}", name],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() == "true"
    except Exception:
        return False


def _remove_container(name: str) -> None:
    try:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15)
    except Exception:
        log.warning("Could not remove container %s", name)


# ----------------------------------------------------------------- local ---

def _run_local(code: str, input_data: str, time_limit_ms: int) -> RunResult:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        path = os.path.join(tmp, "solution.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, "-I", path],
                input=input_data,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=time_limit_ms / 1000,
                cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return RunResult("time_limit_exceeded", runtime_ms=time_limit_ms)
        elapsed = int((time.perf_counter() - start) * 1000)

    if proc.returncode != 0:
        return RunResult("runtime_error", proc.stdout, proc.stderr[-2000:], elapsed)
    return RunResult("ok", proc.stdout[:MAX_OUTPUT_CHARS], proc.stderr, elapsed)


def outputs_match(actual: str, expected: str) -> bool:
    """Ignore trailing spaces on each line and blank lines at the end."""

    def normalize(text: str) -> list[str]:
        return [line.rstrip() for line in text.strip().splitlines()]

    return normalize(actual) == normalize(expected)
