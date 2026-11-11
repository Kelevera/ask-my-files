import re

import pytest

from askfiles.answerer import Answer, Citation
from askfiles.chunker import Chunk
from eval import make_corpus, run

WORDS = make_corpus.ADJECTIVES + make_corpus.NOUNS
NAME = r"Project ([A-Z][a-z]+ [A-Z][a-z]+)"


class PerfectClient:
    """Embeds by project-name words and answers by looking the fact up in the prompt."""

    def embed(self, texts):
        return [[1.0 if word in text else 0.0 for word in WORDS] for text in texts]

    def chat(self, system, user):
        sources, question = user.rsplit("Question:", 1)
        name = re.search(NAME, question).group(1)
        for number, block in enumerate(re.split(r"\n\n(?=\[\d+\] \()", sources), start=0):
            match = re.search(rf"Project {name} is\s+([A-Z]{{3}}-\d{{4}})", block)
            if match:
                return f"The access code is {match.group(1)} [{number or 1}]."
        return "NOT_IN_DOCUMENTS"


QUESTION = {"id": "Q01", "question": "What is the access code for Project Amber Falcon?",
            "answerable": True, "expected_code": "ABC-1234",
            "expected_file": "reports/doc01.pdf", "expected_label": "page 2"}
UNANSWERABLE = {"id": "Q02", "question": "What is the access code for Project Jade Raven?",
                "answerable": False, "expected_code": None, "expected_file": None,
                "expected_label": None}


def _answer(text="The code is ABC-1234 [1].", refused=False, cited=("reports/doc01.pdf", "page 2"),
            retrieved=("reports/doc01.pdf",)):
    sources = [Chunk(f"D:/data/{file}", "page 1", "text") for file in retrieved]
    citations = [] if refused or cited is None else [Citation(f"D:/data/{cited[0]}", cited[1])]
    return Answer(text, refused, citations, [0.9] * len(sources), sources)


def test_score_question_correct_answer():
    assert run.score_question(QUESTION, _answer(), "D:/data") == {
        "recall": True, "citation": True, "problem": ""}


@pytest.mark.parametrize("result, recall, problem", [
    (_answer(text="The code is XXX-0000 [1]."), True, "expected code not in answer"),
    (_answer(cited=("reports/doc01.pdf", "page 3")), True, "wrong citation"),
    (_answer(cited=("doc09.txt", "page 2")), True, "wrong citation"),
    (_answer(refused=True), True, "refused an answerable question"),
    (_answer(refused=True, retrieved=("doc05.txt",)), False, "expected file not retrieved"),
])
def test_score_question_failures(result, recall, problem):
    scored = run.score_question(QUESTION, result, "D:/data")
    assert scored["recall"] is recall
    assert scored["citation"] is False
    assert problem in scored["problem"]


def test_recall_and_citation_are_scored_independently():
    # A top_k above 5 can answer correctly from a source outside the top 5.
    result = _answer(retrieved=("doc05.txt", "doc06.txt"))
    scored = run.score_question(QUESTION, result, "D:/data")
    assert (scored["recall"], scored["citation"]) == (False, True)
    assert scored["problem"] == "expected file not retrieved"


def test_recall_only_counts_the_top_five_sources():
    retrieved = ("a.txt", "b.txt", "c.txt", "d.txt", "e.txt", "reports/doc01.pdf")
    assert run.score_question(QUESTION, _answer(retrieved=retrieved), "D:/data")["recall"] is False


def test_score_unanswerable_question():
    assert run.score_question(UNANSWERABLE, _answer(refused=True), "D:/data") == {
        "refused": True, "problem": ""}
    scored = run.score_question(UNANSWERABLE, _answer(), "D:/data")
    assert scored["refused"] is False and "not refused" in scored["problem"]


def test_metrics_are_ratios_over_the_right_question_groups():
    scored = [
        {"recall": True, "citation": True, "problem": ""},
        {"recall": True, "citation": False, "problem": "x"},
        {"recall": False, "citation": False, "problem": "x"},
        {"recall": True, "citation": True, "problem": ""},
        {"refused": True, "problem": ""},
        {"refused": False, "problem": "x"},
    ]
    assert run.compute_metrics(scored) == {
        "recall@5": 0.75, "citation accuracy": 0.5, "refusal rate": 0.5}


def test_report_shows_numbers_gates_and_failures():
    metrics = {"recall@5": 0.9, "citation accuracy": 0.8667, "refusal rate": 1.0}
    failures = [("Q07", "What is | the code?", "wrong citation", "ZZZ-1 [2]\nmore")]
    report = run.render_report(metrics, failures, {"chat model": "m1"})

    assert "| recall@5 | 0.900 | 0.85 | PASS |" in report
    assert "| citation accuracy | 0.867 | 0.90 | FAIL |" in report
    assert "| refusal rate | 1.000 | 0.90 | PASS |" in report
    assert "Overall: FAIL" in report
    assert "## Failing cases" in report
    assert "| Q07 | What is / the code? | wrong citation | ZZZ-1 [2] more |" in report
    assert "| chat model | m1 |" in report


def test_report_without_failures():
    metrics = {"recall@5": 0.85, "citation accuracy": 0.9, "refusal rate": 0.9}
    report = run.render_report(metrics, [], {})
    assert "Overall: PASS" in report and "FAIL" not in report
    assert "## Failing cases\n\nNone." in report


def test_run_end_to_end_with_a_perfect_fake_client(tmp_path):
    report_path = tmp_path / "EVAL_REPORT.md"
    db_path = tmp_path / "index.sqlite"
    db_path.write_bytes(b"stale content that is not a database")

    metrics = run.run(PerfectClient(), data_dir=tmp_path / "data", db_path=db_path,
                      questions_path=tmp_path / "questions.json", report_path=report_path)

    assert metrics == {"recall@5": 1.0, "citation accuracy": 1.0, "refusal rate": 1.0}
    report = report_path.read_text(encoding="utf-8")
    for section in ["# Eval report", "## Results", "## Settings", "## Failing cases"]:
        assert section in report
    assert "Overall: PASS" in report
    assert len(list((tmp_path / "data").rglob("*.*"))) == 25


def test_run_reports_failures_of_a_client_that_never_refuses(tmp_path):
    class NeverRefuses(PerfectClient):
        def chat(self, system, user):
            reply = super().chat(system, user)
            return "The code is AAA-0000 [1]." if reply == "NOT_IN_DOCUMENTS" else reply

    report_path = tmp_path / "EVAL_REPORT.md"
    metrics = run.run(NeverRefuses(), data_dir=tmp_path / "data", db_path=tmp_path / "i.sqlite",
                      questions_path=tmp_path / "questions.json", report_path=report_path)

    assert metrics["refusal rate"] == 0.0
    report = report_path.read_text(encoding="utf-8")
    assert "| refusal rate | 0.000 | 0.90 | FAIL |" in report
    assert report.count("unanswerable question was not refused") == 10
