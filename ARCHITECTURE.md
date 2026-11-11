# ARCHITECTURE

Derived from BRIEF.md and DECISIONS.md. Requirement IDs refer to SPEC.md.

## Layout
```
src/askfiles/        application package
  __main__.py        entry point for `python -m askfiles`
  config.py          environment variables and defaults
  ollama.py          HTTP client for Ollama (urllib)
  loaders.py         file -> segments
  chunker.py         segments -> chunks
  store.py           SQLite storage
  indexer.py         folder -> store (incremental)
  retriever.py       query -> ranked chunks
  answerer.py        question -> answer, citations, scores
  cli.py             argument parsing and output
  web.py             Flask app
tests/               pytest unit tests (offline, no Ollama needed)
eval/                make_corpus.py, run.py, questions.json; eval/data/ is generated
install.ps1, run.ps1 Windows setup and start scripts
```

## Modules
| Module | Responsibility | Depends on |
|---|---|---|
| config | Read ASKFILES_* variables, provide defaults | os |
| ollama | health(), embed(texts), chat(system, user) against the Ollama HTTP API | urllib, config |
| loaders | Read TXT, MD, PDF, DOCX into segments (path, label, text) | pypdf, python-docx |
| chunker | Split segments into chunks of about 800 characters, 150 overlap | none |
| store | Tables documents and chunks, CRUD functions | sqlite3, numpy |
| indexer | Walk a folder, hash files, embed changed files, remove deleted ones | loaders, chunker, store, embedder |
| retriever | Cosine similarity over all chunks, top_k | numpy, store, embedder |
| answerer | Score threshold, prompt building, refusal, citation extraction | retriever, chat client |
| cli | Commands index and query | indexer, answerer |
| web | One page with a question box, answer and citation list | flask, answerer |

The embedder and the chat client are passed in as arguments, so tests use fakes and never
need a running Ollama.

## Data flow
Indexing:
```
folder -> indexer (walk, sha256) -> loaders (segments) -> chunker (chunks)
       -> ollama.embed (vectors) -> store (documents, chunks)
```
Query:
```
question -> ollama.embed -> retriever (cosine over store.all_chunks, top k)
         -> answerer: top score < ASKFILES_MIN_SCORE -> refusal (no model call)
                      else prompt with sources [1]..[k] -> ollama.chat
                      reply NOT_IN_DOCUMENTS -> refusal
                      else answer + citations (cited [n], or top 2 if none)
         -> cli or web output
```

## Storage
One SQLite file (D02). The CLI and web UI use index.sqlite in the working directory, the eval
uses eval/index.sqlite.

| Table | Columns |
|---|---|
| documents | path TEXT PRIMARY KEY, sha256 TEXT, mtime REAL, size INTEGER |
| chunks | id INTEGER PRIMARY KEY, path TEXT, label TEXT, text TEXT, embedding BLOB |

Embeddings are stored as float32 bytes. Similarity is computed in numpy over all chunks in
memory. No vector index: the target is a personal document folder.

## Interfaces
- CLI: `python -m askfiles index <folder>`, `python -m askfiles query "<question>"`.
- Web: Flask on 127.0.0.1:5000. GET / shows the form, POST / shows answer and citations.
  No route serves document files.
- Ollama HTTP API on ASKFILES_OLLAMA_URL: GET /api/tags (health and model list),
  POST /api/embed (fallback POST /api/embeddings, D03), POST /api/chat.
- Eval: `python -m eval.run` writes EVAL_REPORT.md.

## Constraints
- Localhost only at runtime (D10). No authentication (D05).
- Dependencies pinned (D09). Python runs from .venv (D01).
