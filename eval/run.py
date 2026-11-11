"""Run the eval: build the corpus, index it, ask every question, write EVAL_REPORT.md.

Run: python -m eval.run
"""
import json
import os
import sys
import urllib.error
from pathlib import Path

from askfiles import config, store
from askfiles.answerer import answer
from askfiles.indexer import index_folder
from askfiles.ollama import OllamaClient

from . import make_corpus

EVAL_DIR = Path(__file__).resolve().parent
DB_PATH = EVAL_DIR / "index.sqlite"
REPORT_PATH = EVAL_DIR.parent / "EVAL_REPORT.md"
GATES = {"recall@5": 0.85, "citation accuracy": 0.90, "refusal rate": 0.90}


def _relative(path, data_dir):
    return Path(os.path.relpath(path, data_dir)).as_posix()


def score_question(question, result, data_dir):
    """Score one answer. Returns the flags for its metrics and a problem text ("" = fine)."""
    if not question["answerable"]:
        problem = "" if result.refused else "unanswerable question was not refused"
        return {"refused": result.refused, "problem": problem}

    retrieved = [_relative(chunk.path, data_dir) for chunk in result.sources[:5]]
    recall = question["expected_file"] in retrieved
    cited = [(_relative(c.path, data_dir), c.label) for c in result.citations]
    problems = []
    if result.refused:
        problems.append("refused an answerable question")
    else:
        if question["expected_code"] not in result.answer:
            problems.append("expected code not in answer")
        if (question["expected_file"], question["expected_label"]) not in cited:
            problems.append("wrong citation")
    citation = not problems
    if not recall:
        problems.append("expected file not retrieved")
    return {"recall": recall, "citation": citation, "problem": ", ".join(problems)}


def compute_metrics(scored):
    def ratio(key):
        values = [item[key] for item in scored if key in item]
        return sum(values) / len(values) if values else 0.0

    return {"recall@5": ratio("recall"), "citation accuracy": ratio("citation"),
            "refusal rate": ratio("refused")}


def _cell(text):
    return " ".join(str(text).replace("|", "/").split())


def render_report(metrics, failures, settings):
    """failures: list of (id, question, problem, answer). settings: {name: value}."""
    passed = {name: metrics[name] >= gate for name, gate in GATES.items()}
    lines = ["# Eval report", "",
             "Synthetic corpus (seed 42): 25 documents, 40 questions (30 answerable, "
             "10 unanswerable).", "",
             "## Results", "",
             "| Metric | Value | Gate | Result |", "|---|---|---|---|"]
    for name, gate in GATES.items():
        lines.append(f"| {name} | {metrics[name]:.3f} | {gate:.2f} | "
                     f"{'PASS' if passed[name] else 'FAIL'} |")
    lines += ["", f"Overall: {'PASS' if all(passed.values()) else 'FAIL'}", "",
              "## Settings", "", "| Setting | Value |", "|---|---|"]
    lines += [f"| {name} | {value} |" for name, value in settings.items()]
    lines += ["", "## Failing cases", ""]
    if failures:
        lines += ["| Id | Question | Problem | Answer |", "|---|---|---|---|"]
        lines += [f"| {_cell(i)} | {_cell(q)} | {_cell(p)} | {_cell(a)} |"
                  for i, q, p, a in failures]
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def run(client, data_dir=make_corpus.DATA_DIR, db_path=DB_PATH,
        questions_path=make_corpus.QUESTIONS_PATH, report_path=REPORT_PATH, cfg=None):
    """Run the whole eval with the given client and return the three metrics."""
    cfg = cfg or config.load()
    questions = make_corpus.generate(data_dir, questions_path)
    if os.path.exists(db_path):
        os.remove(db_path)
    connection = store.connect(db_path)
    try:
        counts = index_folder(connection, data_dir, client.embed)
        print(f"Indexed: {counts}", flush=True)
        scored, failures = [], []
        for question in questions:
            result = answer(connection, client.embed, client.chat, question["question"],
                            min_score=cfg.min_score)
            item = score_question(question, result, data_dir)
            scored.append(item)
            print(f"{question['id']} {'ok' if not item['problem'] else item['problem']}",
                  flush=True)
            if item["problem"]:
                failures.append((question["id"], question["question"], item["problem"],
                                 result.answer))
    finally:
        connection.close()
    metrics = compute_metrics(scored)
    settings = {"chat model": cfg.chat_model, "embed model": cfg.embed_model,
                "min score": cfg.min_score, "chunk size": config.CHUNK_SIZE,
                "chunk overlap": config.CHUNK_OVERLAP, "top k": config.TOP_K}
    Path(report_path).write_text(render_report(metrics, failures, settings), encoding="utf-8")
    return metrics


def main():
    cfg = config.load()
    try:
        metrics = run(OllamaClient(cfg), cfg=cfg)
    except urllib.error.URLError as error:
        print(f"Error: Ollama request to {cfg.ollama_url} failed: {error}. Is Ollama running, "
              f"and are the models {cfg.chat_model} and {cfg.embed_model} pulled?",
              file=sys.stderr)
        return 2
    for name, gate in GATES.items():
        print(f"{name}: {metrics[name]:.3f} (gate {gate:.2f})")
    print(f"Report: {REPORT_PATH}")
    return 0 if all(metrics[name] >= gate for name, gate in GATES.items()) else 1


if __name__ == "__main__":
    sys.exit(main())
