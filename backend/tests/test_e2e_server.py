"""End-to-end: start the real Uvicorn server, compile over HTTP, build and run the C++."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from .helpers import EXAMPLES_DIR, build_and_run_cpp, find_cxx

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    port = _free_port()
    env = dict(os.environ, CORS_ORIGINS="http://localhost:5173")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=BACKEND_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"{base}/health", timeout=1) as r:
                    if r.status == 200:
                        break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        else:
            pytest.fail("server did not start: " + proc.stderr.read().decode(errors="replace"))
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def post(base: str, payload: dict) -> tuple[int, dict]:
    req = urllib.request.Request(f"{base}/compile", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Origin": "http://localhost:5173"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def test_health_over_http(server):
    with urllib.request.urlopen(f"{server}/health") as r:
        assert json.loads(r.read())["status"] == "ok"


def test_error_programs_over_http(server):
    for name, stage in (("error_lexical.cb", "lexical"), ("error_syntax.cb", "syntax"),
                        ("error_semantic.cb", "semantic")):
        status, data = post(server, {"source": (EXAMPLES_DIR / name).read_text(encoding="utf-8")})
        assert status == 200 and data["success"] is False
        assert data["diagnostics"][0]["stage"] == stage
        assert data["cpp"] is None


def test_invalid_request_over_http(server):
    status, data = post(server, {"code": "print(1)"})
    assert status == 422


@pytest.mark.skipif(find_cxx() is None, reason="no C++ compiler available")
@pytest.mark.parametrize("name", ["fizzbuzz.cb", "primes.cb", "types.cb"])
def test_compile_over_http_then_run_cpp(server, name):
    source = (EXAMPLES_DIR / name).read_text(encoding="utf-8")
    status, data = post(server, {"source": source})
    assert status == 200 and data["success"] is True
    expected = (EXAMPLES_DIR / "expected" / name.replace(".cb", ".txt")).read_text(encoding="utf-8")
    assert build_and_run_cpp(data["cpp"]) == expected
