# DECISIONS

Each entry: id, decision, reason. Add new entries at the bottom. Never delete old entries.

- D01 Python 3.12 in a .venv inside the project folder. On Windows, run all Python and pip
  commands through .venv\Scripts\python.exe, not through the bare python command.
  Reason: stable on Windows 11, and the .venv keeps the pinned packages isolated.

- D02 Storage: one SQLite file, embeddings stored as BLOB, cosine similarity in numpy.
  Reason: no server or extra service, and the data is easy to inspect.

- D03 Ollama HTTP API on localhost. Use POST /api/embed for embeddings. If it returns 404,
  fall back to POST /api/embeddings with the field "prompt".
  Reason: no extra Python package needed to reach the models.

- D04 Parsing: pypdf for PDF, python-docx for DOCX, UTF-8 for TXT and MD.
  Reason: small, pure-Python libraries.

- D05 Web UI: Flask, bound to 127.0.0.1 only. No authentication.
  Reason: local use only.

- D06 Chunking: about 800 characters with 150 overlap, never crossing a page or section.
  Reason: a starting point. T14 may tune it, with each change recorded.

- D07 Refusal has two layers: a minimum retrieval score, and the model replying exactly
  NOT_IN_DOCUMENTS. Reason: refusal must not depend on the model alone.

- D08 Eval data is synthetic and deterministic (seed 42), generated into eval/data/ and
  never committed. Reason: reproducible. The eval measures the pipeline, not the user's
  documents.

- D09 Dependencies are pinned in requirements.txt and requirements-dev.txt.
  Reason: the autonomous loop must not break after an upgrade.

- D10 Network: localhost only at runtime. Package installs from PyPI only.
  Reason: privacy, and the constraint in CLAUDE.md.

- D11 Default chat model: qwen2.5:7b. Override with ASKFILES_CHAT_MODEL.
  Reason: fits a typical 16 GB machine. The user may choose another model.

- D12 Use Python 3.11 for the .venv instead of 3.12 (changes D01). Code stays compatible
  with 3.11 and newer. Reason: only Python 3.11.9 is installed on this PC, and installing
  another Python is a system change that CLAUDE.md forbids.

- D13 pytest.ini sets pythonpath to "src" and "." so tests import askfiles and eval without
  installing the package. Reason: simplest setup, no build configuration needed.
- D14 Chat requests use temperature 0 and stream false.
  Reason: repeatable answers for the eval, and one JSON reply is simpler to parse.

- D15 TXT and MD files are one segment with an empty label, so their citation is the file
  name alone. DOCX text before the first heading gets the label "section (start)". Empty
  pages and sections are skipped. DOCX table text is not read.
  Reason: the simplest reading of T03. Plain text has no pages or sections to point to.

- D16 The index stores absolute file paths. A document is removed when its file no longer
  exists on disk. A file that cannot be parsed is logged, counted as "failed" (a fifth
  count next to the four in T06) and skipped.
  Reason: several folders can share one index, and one broken PDF must not stop the run.

- D17 A model reply that contains NOT_IN_DOCUMENTS anywhere counts as a refusal. A refusal
  returns a fixed message and no citations. Only [n] numbers that match a source count as
  citations. Reason: small models often add punctuation or a citation to the marker.

- D18 pyproject.toml makes the package installable, and the .venv gets it with
  "pip install -e ." (install.ps1 does this in T13). The CLI has an optional --db argument
  (default index.sqlite in the current folder).
  Reason: "python -m askfiles" must work from any folder although the code lives in src/.

- D19 eval/questions.json is committed (it is deterministic), eval/data/ is not (D08).
  DOCX files are re-zipped with a fixed timestamp and PDFs use reportlab's invariant mode.
  Reason: both formats embed the current time otherwise, which breaks byte-identical runs.

- D20 Eval scoring: recall@5 looks at the first 5 retrieved chunks. A citation is correct when
  the answer is not a refusal, contains the expected code, and one of its citations has the
  expected file and label. The two metrics are scored independently. python -m eval.run
  also regenerates the corpus and exits with 0 (all gates pass), 1 (a gate fails) or 2
  (Ollama not usable). Chunk size, overlap and top k are constants in askfiles/config.py,
  so that T14 tunes the real defaults. Reason: the simplest reading of T11 and BRIEF.md.
