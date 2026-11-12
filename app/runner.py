"""Runs a user's Python code against one input and reports what happened.

WARNING: this runs code directly on your machine with only a timeout.
It is NOT safe for untrusted users. Week 3 moves this into Docker.
"""
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

MAX_OUTPUT_CHARS = 100_000


@dataclass
class RunResult:
    status: str  # "ok", "runtime_error", "time_limit_exceeded"
    stdout: str = ""
    stderr: str = ""
    runtime_ms: int = 0


def run_python(code: str, input_data: str, time_limit_ms: int) -> RunResult:
    with tempfile.TemporaryDirectory() as tmp:
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
