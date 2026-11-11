# CLAUDE.md: working rules

## Session start (every session)
1. Read STATUS.md. If its first line is STATE: DONE or STATE: BLOCKED, stop and do nothing.
2. Read PLAN.md and DECISIONS.md. Work only on the first unchecked task in PLAN.md.
3. If ARCHITECTURE.md or SPEC.md is missing, create them first from BRIEF.md and DECISIONS.md.
   SPEC.md lists functional requirements with IDs. ARCHITECTURE.md lists modules, data flow,
   storage and interfaces. Commit both, then continue with the task.

## Work loop (per task)
- Write a failing test that describes the task's acceptance. Run pytest and confirm it fails.
- Implement the smallest change that makes it pass. Run pytest until everything is green.
- Tick the task in PLAN.md. Update STATUS.md: last done, next task, open issues, session count.
- Commit with the message "T<id>: <title>". Never leave uncommitted changes.
- Then start the next task in the same session.

## Session limit safety
- Commit and update STATUS.md at every task boundary.
- If you sense the session is near its limit, finish the current commit, write STATUS.md
  completely, and stop at the boundary. The next session resumes from STATUS.md.

## Decisions and questions
- Never ask the user a question. When something is unclear, choose the simplest option that
  meets BRIEF.md, record it in DECISIONS.md with a one-line reason, and proceed.
- Follow DECISIONS.md. For any change of approach, add a new entry. Never delete old entries.

## Stop conditions
- First line of STATUS.md is exactly `STATE: DONE` when every PLAN task is ticked and
  EVAL_REPORT.md shows PASS for all three gates in BRIEF.md.
- First line is exactly `STATE: BLOCKED`, followed by a reason, when the same task failed
  three times in a row, or the eval gates still fail after the three tuning rounds in T14.
  Include the numbers. Commit before stopping.
- Otherwise the first line is exactly `STATE: IN_PROGRESS`.

## Constraints
- Work only inside this folder.
- Network: localhost (Ollama) and package installs from PyPI only. No other downloads.
- No secrets, API keys or personal data in the repo or in generated files.
- Code, comments and docs in English.
- Use only the commands the work needs: python, pip, pytest, git, ollama.
  Do not change system settings or touch files outside this folder.