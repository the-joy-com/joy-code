# AGENTS.md

This repository is designed for long-running coding-agent work. The goal is not to maximize raw code output. The goal is to leave the repo in a state where the next session can continue without guessing.

## Startup Workflow

Before writing code:

1. Confirm the working directory with `pwd`.
2. Read the progress file (see Required Artifacts) for the latest verified state and next step.
3. Review recent commits with `git log --oneline -5`.

If baseline verification is already failing, fix that first. Do not stack new feature work on top of a broken starting state.

## Working Rules

- Work on one feature at a time.
- Do not mark a feature complete just because code was added.
- Keep changes within the selected feature scope. If a blocker seems to require a supporting fix outside that scope, stop and ask a human to validate the fix before making it.
- Do not silently change verification rules during implementation.
- Prefer durable repo artifacts over chat summaries.

## Required Artifacts

- The progress file: session log and current verified status. Which file depends on what is being worked on:
  - `harness/state/PROGRESS.md` when working on the Joy coding agent itself.
  - `harness/state/<worked-on-application>/PROGRESS.md` when working on a target application, where `<worked-on-application>` is the application's folder name (for example `harness/state/note-taker/PROGRESS.md` for `examples/note-taker`).

  The progress file is a running summary, not an append-only log. When it gets bloated, or fills up with entries that matter little to the task at hand, condense it: merge or shorten older session entries and drop details the code or git history already records. Always keep the current verified state, the next step, open risks and blockers, and the full test and verification evidence for the current task.
- `session-handoff.md`: optional compact handoff for larger sessions, next to the progress file.

## Definition Of Done

A task is done only when all of the following are true:

1. The target behavior is implemented.
2. The application's tests pass locally.
3. The application's verification checks pass.
4. The progress file records the task in its session log, with evidence that the tests and verification checks actually ran and passed.
5. The repository remains restartable from the standard startup path.

The tests and verification checks depend on the application being worked on. When that is an application other than the Joy coding agent itself (for example `examples/note-taker`), use the commands that application's documentation explicitly gives (its `README.md`, `ARCHITECTURE.md` or `AGENTS.md`, or existing pieces of `*.md` documentation that exist within the project). Do not guess or invent commands. If the documentation names none, say so in the progress file and ask a human how the work should be verified.

Tracking features and their state is the responsibility of the humans developing the application, not of the coding agent: do not create or update a features list.

## End Of Session

Before ending a session:

1. Update the progress file, condensing it first if it has grown bloated (see Required Artifacts).
2. Record any unresolved risk or blocker.
3. Add to git staging area modified files with a descriptive message once the work is in a safe state _then_ ask for a human to review the work.
4. Leave the repo clean enough for the next session to run using the standard startup path.
