STATE: IN_PROGRESS

Last done: T13 Windows scripts.
Next task: T14
Open issues:
- T14 needs the Ollama models qwen2.5:7b and nomic-embed-text. At the start of session 1
  no model was installed. During T13, nomic-embed-text appeared in `ollama list` (pulled
  outside this session). qwen2.5:7b was still missing at that time. Pulling models is a
  download outside PyPI, which CLAUDE.md does not allow the agent to do. Check with
  `.\install.ps1 -ChecksOnly` before running the eval.
- Only Python 3.11 is installed, so the .venv uses 3.11 (D12).
Session count: 1
