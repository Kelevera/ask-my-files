import json
import re
from pathlib import Path

import pypdf
import pytest

from askfiles.loaders import load_file
from eval import make_corpus

FACT = re.compile(r"The access code for Project ([A-Z][a-z]+ [A-Z][a-z]+) is ([A-Z]{3}-\d{4})\.")


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    root = tmp_path_factory.mktemp("corpus")
    make_corpus.generate(root / "data", root / "questions.json")
    return root


def _files(root):
    return sorted(p for p in (root / "data").rglob("*") if p.is_file())


def _facts(root):
    """{project name: (code, relative file, label)} as read back by the real loaders."""
    facts = {}
    for path in _files(root):
        for segment in load_file(path):
            for name, code in FACT.findall(" ".join(segment.text.split())):
                assert name not in facts, "each project is planted once"
                facts[name] = (code, path.relative_to(root / "data").as_posix(), segment.label)
    return facts


def test_two_runs_are_byte_identical(corpus, tmp_path):
    make_corpus.generate(tmp_path / "data", tmp_path / "questions.json")
    first = {p.relative_to(corpus).as_posix(): p.read_bytes() for p in corpus.rglob("*") if p.is_file()}
    second = {p.relative_to(tmp_path).as_posix(): p.read_bytes()
              for p in tmp_path.rglob("*") if p.is_file()}
    assert first.keys() == second.keys()
    assert [name for name in first if first[name] != second[name]] == []


def test_rerun_into_the_same_folder_removes_stale_files(tmp_path):
    make_corpus.generate(tmp_path / "data", tmp_path / "questions.json")
    (tmp_path / "data" / "stale.txt").write_text("old", encoding="utf-8")
    make_corpus.generate(tmp_path / "data", tmp_path / "questions.json")
    assert not (tmp_path / "data" / "stale.txt").exists()


def test_corpus_shape(corpus):
    files = _files(corpus)
    assert len(files) == 25
    assert {p.suffix for p in files} == {".pdf", ".docx", ".txt", ".md"}
    assert any(p.parent != corpus / "data" for p in files), "some files are in subfolders"
    long_pdfs = [p for p in files if p.suffix == ".pdf" and len(pypdf.PdfReader(p).pages) >= 3]
    assert len(long_pdfs) >= 2


def test_every_document_has_two_or_three_facts(corpus):
    per_file = {}
    for _, file, _ in _facts(corpus).values():
        per_file[file] = per_file.get(file, 0) + 1
    assert len(per_file) == 25
    assert set(per_file.values()) == {2, 3}


def test_questions_match_the_planted_facts(corpus):
    questions = json.loads((corpus / "questions.json").read_text(encoding="utf-8"))
    facts = _facts(corpus)
    answerable = [q for q in questions if q["answerable"]]
    unanswerable = [q for q in questions if not q["answerable"]]

    assert (len(questions), len(answerable), len(unanswerable)) == (40, 30, 10)
    assert len({q["question"] for q in questions}) == 40
    for q in answerable:
        name = re.search(r"Project ([A-Z][a-z]+ [A-Z][a-z]+)", q["question"]).group(1)
        assert facts[name] == (q["expected_code"], q["expected_file"], q["expected_label"])
    for q in unanswerable:
        name = re.search(r"Project ([A-Z][a-z]+ [A-Z][a-z]+)", q["question"]).group(1)
        assert name not in facts
        assert q["expected_code"] is None


def test_answerable_questions_cover_pages_beyond_the_first_and_sections(corpus):
    questions = json.loads((corpus / "questions.json").read_text(encoding="utf-8"))
    labels = {q["expected_label"] for q in questions if q["answerable"]}
    assert any(label.startswith("page ") and label != "page 1" for label in labels)
    assert any(label.startswith("section ") for label in labels)
    assert "" in labels


def test_default_paths_point_into_the_eval_folder():
    eval_dir = Path(make_corpus.__file__).resolve().parent
    assert make_corpus.DATA_DIR == eval_dir / "data"
    assert make_corpus.QUESTIONS_PATH == eval_dir / "questions.json"
