# Ask My Files

A local, private question-answering tool over a folder of documents (PDF, DOCX, TXT, MD).
It runs entirely on your PC with Ollama. At runtime it only talks to Ollama on localhost.
Every answer names its sources: the file and the page (PDF) or section (DOCX).
If the documents do not contain the answer, it says so instead of guessing.

## Requirements

- Windows 11 with PowerShell.
- Python 3.11 or newer from https://www.python.org (tick "Add python.exe to PATH").
- Ollama from https://ollama.com.
- About 6 GB of free disk space for the two models, and 16 GB of RAM.

## Install

Plan about 20 minutes. Most of it is the model download (about 5 GB).

1. Install Python and Ollama (see Requirements). Ollama starts by itself after its setup.
2. Open PowerShell and pull the two models:

   ```powershell
   ollama pull qwen2.5:7b
   ollama pull nomic-embed-text
   ```

3. Go to the project folder and run the installer:

   ```powershell
   cd C:\path\to\ask-my-files
   .\install.ps1
   ```

   It creates `.venv`, installs the packages, and checks Ollama and both models. Each check
   prints an `[OK]` or `[FAIL]` line. A `[FAIL]` line says what to do. Fix it and run
   `.\install.ps1` again. `.\install.ps1 -ChecksOnly` repeats only the Ollama and model checks.

If PowerShell refuses to run the script, start it like this instead:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

## Usage

Run all commands in the project folder. The index is the file `index.sqlite` in the folder
you run the commands from, and the web page reads it from the project folder.

1. Index your documents. Subfolders are included.

   ```powershell
   .\.venv\Scripts\python.exe -m askfiles index C:\path\to\documents
   ```

   It prints the counts, for example `added: 12, updated: 0, unchanged: 0, removed: 0, failed: 0`.
   Run the same command again after you add, change or delete files. Only changed files are
   read again.

2. Ask on the command line:

   ```powershell
   .\.venv\Scripts\python.exe -m askfiles query "What is the notice period in the rental contract?"
   ```

   The output is the answer, followed by `Sources:` with one line per source, such as
   `contract.pdf, page 3` or `handbook.docx, section Holidays`.

3. Or ask in the browser:

   ```powershell
   .\run.ps1
   ```

   Open http://127.0.0.1:5000, type a question, and read the answer with its citations.
   Press Ctrl+C in PowerShell to stop the page.

To keep the index somewhere else, put `--db` before the command:
`.\.venv\Scripts\python.exe -m askfiles --db D:\my.sqlite index C:\path\to\documents`.
The web page always uses `index.sqlite` in the project folder.

### Settings

Set these environment variables before a command to change the defaults, for example
`$env:ASKFILES_CHAT_MODEL = "llama3.1:8b"`.

| Variable | Default | Meaning |
|---|---|---|
| `ASKFILES_CHAT_MODEL` | `qwen2.5:7b` | Model that writes the answer. |
| `ASKFILES_EMBED_MODEL` | `nomic-embed-text` | Model that turns text into vectors. Re-index from an empty index after changing it. |
| `ASKFILES_OLLAMA_URL` | `http://localhost:11434` | Address of Ollama. |
| `ASKFILES_MIN_SCORE` | `0.35` | Minimum retrieval score. Below it the tool refuses without asking the model. |

## Limits

- Scanned PDFs without a text layer give no text. There is no OCR.
- Text inside DOCX tables is not read.
- TXT and MD files are cited by file name only. They have no pages or sections.
- A file that cannot be read is counted as `failed` and skipped.
- The answer comes from the 5 best-matching text chunks. Questions that need a whole
  document, such as summaries or counts, work poorly.
- The tool can still refuse a question the documents do answer, or cite the wrong passage.
  Check the cited page for anything important.
- Local use by one person only: no login, no multi-user access, no cloud sync. The web page
  listens on 127.0.0.1 and does not serve the files themselves.
- The index stores the text of your documents unencrypted in `index.sqlite`.
- It is not legal advice.

## Run the eval

The eval creates 25 synthetic documents and 40 questions with known answers (seed 42),
indexes them, asks every question, and writes `EVAL_REPORT.md`. It does not touch your own
index. It takes about 12 minutes.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m eval.run
```

| Gate | Required |
|---|---|
| recall@5 (the right file is among the 5 retrieved chunks) | at least 0.85 |
| citation accuracy (right answer, right file and page or section) | at least 0.90 |
| refusal rate (unanswerable questions are refused) | at least 0.90 |

The exit code is 0 when all gates pass, 1 when a gate fails, and 2 when Ollama or a model is
not usable. The eval measures the pipeline on synthetic documents. Test the quality on your
own documents afterwards.

To run the unit tests (no Ollama needed):

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Troubleshooting

| Message or symptom | What to do |
|---|---|
| `[FAIL] Ollama does not answer` | Start Ollama from the Start menu, then run `.\install.ps1 -ChecksOnly`. |
| `[FAIL] Model '...' is not installed` | Run the `ollama pull` command shown in the message. |
| `[FAIL] Could not create .venv` | Install Python 3.11 or newer and run `.\install.ps1` again. |
| `Error: Ollama request ... failed` | Ollama is not running or a model is missing. Run `.\install.ps1 -ChecksOnly`. |
| Every question is refused | Index the folder first, and run the commands in the project folder. |
| The first answer is slow | Ollama loads the model on the first question. Later answers are faster. |
