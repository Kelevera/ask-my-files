import importlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_package_imports():
    assert importlib.import_module("askfiles").__name__ == "askfiles"
    assert importlib.util.find_spec("askfiles.__main__") is not None


def _pinned(name):
    lines = (ROOT / name).read_text(encoding="utf-8").split()
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*", line) for line in lines)
    return {line.split("==")[0].lower() for line in lines}


def test_requirements_are_pinned():
    assert _pinned("requirements.txt") == {"pypdf", "python-docx", "numpy", "flask"}
    assert _pinned("requirements-dev.txt") == {"pytest", "reportlab"}


def test_gitignore_entries():
    entries = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
    for required in [".venv/", "__pycache__/", "index.sqlite", "eval/index.sqlite",
                     "eval/data/", "run.log"]:
        assert required in entries


def test_readme_covers_install_usage_limits_and_eval():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for heading in ["## Install", "## Usage", "## Limits", "## Run the eval", "## Troubleshooting"]:
        assert heading in readme
    for command in [r".\install.ps1", r".\run.ps1", "ollama pull qwen2.5:7b",
                    "ollama pull nomic-embed-text", "-m askfiles index", "-m askfiles query",
                    "pip install -r requirements-dev.txt", "-m eval.run", "-m pytest",
                    "http://127.0.0.1:5000"]:
        assert command in readme, command
    for variable in ["ASKFILES_CHAT_MODEL", "ASKFILES_EMBED_MODEL", "ASKFILES_OLLAMA_URL",
                     "ASKFILES_MIN_SCORE"]:
        assert variable in readme
