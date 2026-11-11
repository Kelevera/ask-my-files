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


def test_readme_exists():
    assert (ROOT / "README.md").is_file()
