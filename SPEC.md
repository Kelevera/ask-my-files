# SPEC

Functional requirements for Ask My Files. Derived from BRIEF.md and DECISIONS.md.
Each requirement names the PLAN task that delivers it.

## Indexing
- FR-01 Walk a folder recursively and index files with the extensions .pdf, .docx, .txt, .md. (T06)
- FR-02 TXT and MD are read as UTF-8, one segment per file. (T03)
- FR-03 PDF is read with pypdf, one segment per page, labelled "page N" (N starts at 1). (T03)
- FR-04 DOCX is read with python-docx, one segment per Heading-style section, labelled
  "section <heading>". (T03)
- FR-05 Segments are split into chunks of about 800 characters with 150 characters overlap.
  A chunk never crosses a page or section boundary and keeps its file path and label. (T04)
- FR-06 Indexing is incremental: a file whose sha256 is unchanged is skipped, a changed file is
  re-embedded, and a file that no longer exists is removed from the index. (T06)
- FR-07 Indexing reports the counts added, updated, unchanged, removed. (T06)

## Storage
- FR-08 The index is one SQLite file at a caller-given path, with tables
  documents(path PK, sha256, mtime, size) and chunks(id, path, label, text, embedding BLOB). (T05)

## Models
- FR-09 Configuration comes from environment variables: ASKFILES_CHAT_MODEL (default qwen2.5:7b),
  ASKFILES_EMBED_MODEL (default nomic-embed-text), ASKFILES_OLLAMA_URL (default
  http://localhost:11434), ASKFILES_MIN_SCORE (default 0.35). (T02, T08)
- FR-10 The Ollama client offers health(), embed(list of strings) and chat(system, user) over
  HTTP with urllib. Embeddings use POST /api/embed and fall back to POST /api/embeddings with
  the field "prompt" when the first returns 404. (T02)
- FR-11 No network call leaves localhost at runtime. (T02)

## Retrieval and answering
- FR-12 Retrieval ranks all chunks by cosine similarity to the query embedding and returns the
  top k with scores, highest first. (T07)
- FR-13 The prompt lists the retrieved chunks as numbered sources [1]..[k]. The system prompt
  demands: answer only from the sources, cite them as [n], and reply exactly NOT_IN_DOCUMENTS
  when the answer is not in the sources. (T08)
- FR-14 The tool refuses without calling the chat model when the top score is below
  ASKFILES_MIN_SCORE. (T08)
- FR-15 The tool refuses when the model replies NOT_IN_DOCUMENTS. (T08)
- FR-16 Citations are the sources the answer cites as [n]. If the answer cites none, the top 2
  sources are cited. (T08)
- FR-17 A response contains the answer, the citations (file and label) and the scores. (T08)

## Interfaces
- FR-18 `python -m askfiles index <folder>` prints the index counts. (T09)
- FR-19 `python -m askfiles query "<question>"` prints the answer and the citations as
  "file, page N" or "file, section X". (T09)
- FR-20 A Flask web page on 127.0.0.1:5000 offers a question box and shows the answer and a
  citation list (file name and page or section). It does not serve the files themselves. (T12)
- FR-21 install.ps1 creates .venv, installs requirements.txt, and checks that Ollama answers on
  the configured URL and that both models are listed, with a readable message per failed
  check. run.ps1 starts the web UI. (T13)

## Evaluation
- FR-22 eval/make_corpus.py creates, seeded with random.Random(42), 25 synthetic documents in
  eval/data/ and eval/questions.json with 40 questions (30 answerable, 10 unanswerable). Two
  runs produce byte-identical output. (T10)
- FR-23 `python -m eval.run` rebuilds eval/index.sqlite, runs every question and writes
  EVAL_REPORT.md with recall@5, citation accuracy, refusal rate, PASS/FAIL per gate and a
  table of failing cases. (T11)
- FR-24 Gates: recall@5 >= 0.85, citation accuracy >= 0.90, refusal rate >= 0.90. (T14)

## Documentation
- FR-25 README lets a stranger install and run the tool in under 30 minutes and covers usage,
  limits and how to run the eval. (T15)

## Out of scope
Legal advice, multi-user access, authentication, cloud sync, mobile.
