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
