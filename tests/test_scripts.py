import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
pytestmark = pytest.mark.skipif(POWERSHELL is None, reason="needs PowerShell")


@pytest.fixture
def fake_ollama():
    """A local server that answers /api/tags with a configurable model list."""
    models = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"models": [{"name": name} for name in models]}).encode()
            self.send_response(200 if self.path == "/api/tags" else 404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}", models
    server.shutdown()
    server.server_close()


def _checks(url, **extra_env):
    env = {**os.environ, "ASKFILES_OLLAMA_URL": url, **extra_env}
    for name in ["ASKFILES_CHAT_MODEL", "ASKFILES_EMBED_MODEL"]:
        if name not in extra_env:
            env.pop(name, None)
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(ROOT / "install.ps1"), "-ChecksOnly"],
        capture_output=True, text=True, env=env, timeout=120)


def test_all_checks_pass(fake_ollama):
    url, models = fake_ollama
    models += ["qwen2.5:7b", "nomic-embed-text:latest"]
    result = _checks(url)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("[OK]") == 3
    assert "[FAIL]" not in result.stdout


def test_ollama_not_reachable_prints_a_readable_message():
    result = _checks("http://127.0.0.1:9")
    assert result.returncode == 1
    assert "[FAIL] Ollama does not answer on http://127.0.0.1:9" in result.stdout
    assert "Exception" not in result.stdout + result.stderr


def test_each_missing_model_prints_its_own_message(fake_ollama):
    url, models = fake_ollama
    models += ["some-other-model:latest"]
    result = _checks(url)
    assert result.returncode == 1
    assert "[OK] Ollama answers" in result.stdout
    assert "[FAIL] Model 'qwen2.5:7b' is not installed. Run: ollama pull qwen2.5:7b" in result.stdout
    assert ("[FAIL] Model 'nomic-embed-text' is not installed. Run: ollama pull nomic-embed-text"
            in result.stdout)


def test_checks_use_the_configured_model_names(fake_ollama):
    url, models = fake_ollama
    models += ["llama3:8b", "nomic-embed-text:latest"]
    result = _checks(url, ASKFILES_CHAT_MODEL="llama3:8b")
    assert result.returncode == 0, result.stdout + result.stderr


def test_run_script_starts_the_web_ui_from_the_venv():
    text = (ROOT / "run.ps1").read_text(encoding="utf-8")
    assert r".venv\Scripts\python.exe" in text
    assert "-m askfiles.web" in text


def test_run_script_without_venv_prints_a_readable_message(tmp_path):
    shutil.copy(ROOT / "run.ps1", tmp_path / "run.ps1")
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(tmp_path / "run.ps1")],
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 1
    assert "Run .\\install.ps1 first" in result.stdout
