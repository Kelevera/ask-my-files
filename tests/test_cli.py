import subprocess
import sys
import urllib.error

import pytest

from askfiles import cli


class FakeClient:
    """Embeds by keyword, so that retrieval is predictable without Ollama."""

    def __init__(self, reply="The launch is in May [1]."):
        self.reply = reply

    def embed(self, texts):
        return [[1.0, 0.0] if "launch" in text.lower() else [0.0, 1.0] for text in texts]

    def chat(self, system, user):
        return self.reply


class DownClient:
    def embed(self, texts):
        raise urllib.error.URLError("connection refused")


@pytest.fixture
def docs(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "plan.txt").write_text("The launch is in May.", encoding="utf-8")
    (folder / "food.md").write_text("Soup of the day.", encoding="utf-8")
    return folder


def test_parser_requires_a_command():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([])


def test_parser_reads_index_and_query_arguments():
    parser = cli.build_parser()
    args = parser.parse_args(["index", "C:/docs"])
    assert (args.command, args.folder, args.db) == ("index", "C:/docs", "index.sqlite")
    args = parser.parse_args(["--db", "x.sqlite", "query", "When is the launch?"])
    assert (args.command, args.question, args.db) == ("query", "When is the launch?", "x.sqlite")


def test_index_prints_the_counts(docs, tmp_path, capsys):
    db = str(tmp_path / "i.sqlite")

    assert cli.main(["--db", db, "index", str(docs)], client=FakeClient()) == 0
    assert capsys.readouterr().out.strip() == \
        "added: 2, updated: 0, unchanged: 0, removed: 0, failed: 0"

    cli.main(["--db", db, "index", str(docs)], client=FakeClient())
    assert capsys.readouterr().out.strip() == \
        "added: 0, updated: 0, unchanged: 2, removed: 0, failed: 0"


def test_query_prints_the_answer_and_the_cited_file(docs, tmp_path, capsys):
    db = str(tmp_path / "i.sqlite")
    cli.main(["--db", db, "index", str(docs)], client=FakeClient())
    capsys.readouterr()

    assert cli.main(["--db", db, "query", "When is the launch?"], client=FakeClient()) == 0

    assert capsys.readouterr().out.splitlines() == [
        "The launch is in May [1].", "", "Sources:", "- plan.txt"]


def test_format_answer_shows_page_and_section_citations():
    from askfiles.answerer import Answer, Citation
    result = Answer("Yes [1][2].", False,
                    [Citation("C:/d/a.pdf", "page 4"), Citation("C:/d/b.docx", "section Budget")],
                    [0.9, 0.8], [])
    assert cli.format_answer(result).splitlines() == [
        "Yes [1][2].", "", "Sources:", "- a.pdf, page 4", "- b.docx, section Budget"]


def test_refusal_prints_only_the_refusal_message(docs, tmp_path, capsys):
    db = str(tmp_path / "i.sqlite")
    cli.main(["--db", db, "index", str(docs)], client=FakeClient())
    capsys.readouterr()

    cli.main(["--db", db, "query", "launch?"], client=FakeClient(reply="NOT_IN_DOCUMENTS"))

    assert capsys.readouterr().out.strip() == "I cannot find the answer in your documents."


def test_unreachable_ollama_gives_a_readable_error(docs, tmp_path, capsys):
    code = cli.main(["--db", str(tmp_path / "i.sqlite"), "index", str(docs)], client=DownClient())
    captured = capsys.readouterr()
    assert code == 1
    assert "Ollama" in captured.err and "Traceback" not in captured.err


def test_missing_folder_gives_a_readable_error(tmp_path, capsys):
    code = cli.main(["--db", str(tmp_path / "i.sqlite"), "index", str(tmp_path / "nope")],
                    client=FakeClient())
    assert code == 1
    assert "not a folder" in capsys.readouterr().err


def test_python_dash_m_askfiles_runs():
    result = subprocess.run([sys.executable, "-m", "askfiles", "--help"],
                            capture_output=True, text=True, cwd=sys.prefix)
    assert result.returncode == 0
    assert "index" in result.stdout and "query" in result.stdout
