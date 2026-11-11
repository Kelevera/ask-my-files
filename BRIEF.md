# Ask My Files

## Goal
A local, private question-answering tool over a folder of my documents.
Runs entirely on this PC with Ollama. No cloud calls at runtime.
Stack and architecture decisions: see DECISIONS.md.

## Inputs
A folder with PDF, DOCX, TXT and MD files, possibly nested.

## Must do
1. Index the folder incrementally. Re-index only changed files.
2. Answer questions with citations: file name and page (or section).
3. Refuse to answer when the documents don't contain the answer.
4. CLI: `python -m askfiles index <folder>` and `python -m askfiles query "<question>"`.
5. A local web page on 127.0.0.1 with a question box and visible citations.
6. One-command install and run on Windows 11 (install.ps1 and run.ps1).

## Out of scope
Legal advice, multi-user access, authentication, cloud sync, mobile.

## Done (acceptance gate)
- `python -m eval.run` generates synthetic test documents and 40 questions
  with known answers, then scores the system against them.
- Retrieval recall@5 is at least 0.85.
- Citations point to the correct file and page in at least 0.90 of answers.
- Unanswerable questions are refused in at least 0.90 of cases.
- EVAL_REPORT.md contains these numbers, PASS/FAIL per gate, and the failures.
- README lets a stranger install and run it in under 30 minutes.

Note: the eval uses synthetic documents, so it measures the pipeline.
Real quality shows on your own documents, which you test afterwards.