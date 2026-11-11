# PLAN

Work top to bottom. One task = one commit. Tick a task with [x] when its acceptance passes.
Each task: failing test first, then implementation, then pytest green.

- [x] T01 Project skeleton. requirements.txt (pinned): pypdf, python-docx, numpy, flask.
  requirements-dev.txt (pinned): pytest, reportlab (used only by the eval corpus generator).
  Package folder src/askfiles/ with __init__.py and __main__.py. tests/ folder with a pytest
  config. .gitignore must include: .venv/, __pycache__/, index.sqlite, eval/index.sqlite,
  eval/data/, run.log. README.md stub.
  Accept: pytest runs without errors.

- [x] T02 Config and Ollama client. Read ASKFILES_CHAT_MODEL (default qwen2.5:7b),
  ASKFILES_EMBED_MODEL (default nomic-embed-text), ASKFILES_OLLAMA_URL (default
  http://localhost:11434). Client methods: health(), embed(list of strings), chat(system, user).
  Use urllib from the standard library. Tests mock HTTP. Follow D03 for the embed endpoint.
  Accept: unit tests pass offline.

- [x] T03 Loaders. TXT and MD as UTF-8. PDF with pypdf, one segment per page, label "page N".
  DOCX with python-docx, segments by Heading style, label "section <heading>".
  Each segment carries: file path, label, text.
  Accept: tests with small fixtures created in tmp_path.

- [x] T04 Chunker. About 800 characters per chunk, 150 characters overlap. Never cross a page
  or section boundary. Each chunk keeps its file path and label.
  Accept: tests for overlap, boundaries and empty input.

- [x] T05 Store. SQLite at a path given by the caller. Table documents(path PK, sha256, mtime,
  size). Table chunks(id, path, label, text, embedding BLOB). Functions: upsert_document,
  replace_chunks, delete_document, all_chunks, document_state.
  Accept: CRUD tests on a temporary database.

- [x] T06 Indexer. Walk a folder recursively for .pdf .docx .txt .md. Skip files whose sha256
  is unchanged. Re-embed changed files. Remove documents that no longer exist. Return counts:
  added, updated, unchanged, removed.
  Accept: tests with a fake embedder, including a changed file and a deleted file.

- [x] T07 Retriever. Cosine similarity with numpy. top_k(query, k) returns chunks with scores,
  highest first.
  Accept: tests with hand-made vectors.

- [x] T08 Answerer. Build a prompt with numbered sources [1]..[k]. The system prompt says:
  answer only from the sources, cite them as [n], and if the answer is not in the sources,
  reply exactly NOT_IN_DOCUMENTS. Refuse without calling the model when the top score is below
  ASKFILES_MIN_SCORE (default 0.35). Citations are the sources the answer cites. If none are
  cited, cite the top 2. The response includes answer, citations (file and label) and scores.
  Accept: tests with a fake chat client, covering refusal by score and by model reply.

- [x] T09 CLI. `python -m askfiles index <folder>` prints the index counts.
  `python -m askfiles query "<question>"` prints the answer and the citations as
  "file, page N" or "file, section X".
  Accept: tests for argument parsing and output format.

- [x] T10 Synthetic corpus. eval/make_corpus.py, seeded with random.Random(42). Creates 25
  documents in eval/data/ (PDF, DOCX, TXT, MD; some in subfolders; some PDFs with 3 or more
  pages). Each document has 2 to 3 planted facts of the form "The access code for Project
  <name> is <CODE>", placed on known pages or sections. Writes eval/questions.json with
  40 questions: 30 answerable (expected code, expected file, expected label) and 10
  unanswerable (asking for codes that were never planted).
  Accept: running it twice produces byte-identical output.

- [x] T11 Eval runner. eval/run.py rebuilds eval/index.sqlite from scratch on eval/data/, runs
  every question, and computes: recall@5 (expected file in the top 5 retrieved chunks),
  citation accuracy (answer contains the expected code AND the cited file and label match),
  refusal rate (unanswerable questions refused). Writes EVAL_REPORT.md with the three numbers,
  PASS/FAIL per gate, and a table of failing cases. Command: python -m eval.run.
  Accept: runs end to end, and EVAL_REPORT.md contains all required sections.

- [x] T12 Web UI. Flask app bound to 127.0.0.1:5000. A question box, the answer, and a
  citation list (file name and page or section). Do not serve the files themselves.
  Accept: Flask test client tests for the page and for a query.

- [x] T13 Windows scripts. install.ps1: create .venv, pip install -r requirements.txt, check that
  Ollama answers on the configured URL and that both models are listed. Print a clear message
  for each failed check. run.ps1: start the web UI.
  Accept: install.ps1 runs in a clean folder, and each failed check prints a readable message.

- [x] T14 Tune and measure. Run python -m eval.run. If a gate fails, adjust chunk size
  (600 to 1200 characters), top_k (5 to 8), ASKFILES_MIN_SCORE, or the prompt. At most
  three tuning rounds. Record each round in DECISIONS.md with the numbers before and after.
  Accept: all three gates PASS, or the three rounds are recorded and the task ends in
  STATE: BLOCKED per CLAUDE.md.

- [x] T15 Final. README: install in under 30 minutes, usage, limits, how to run the eval.
  Full pytest run green. EVAL_REPORT.md regenerated. Set the first line of STATUS.md to
  STATE: DONE.
  Accept: a clean install from the README works, and all gates PASS.