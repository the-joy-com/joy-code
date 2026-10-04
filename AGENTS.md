# AGENTS.md

This repository is designed for long-running coding-agent work. The goal is not to maximize raw code output. The goal is to leave the repo in a state where the next session can continue without guessing.

## Session Start (Clock In)

Before writing code:

1. Confirm the working directory with `pwd`.
2. Read the handoff file if there is one, then the progress file (see Required Artifacts), for the latest verified state and next step.
3. Read the decisions file for the design decisions that still govern the code.
4. Review recent commits with `git log --oneline -5`.
5. Run the application's verification check to confirm the repo is in a consistent state. Use the command its documentation gives (see Definition Of Done), for example `uv run pytest` for `examples/note-taker`. Never invent one: if the documentation names none, say so in the progress file and ask a human how to verify.
6. Continue from the next step recorded in the progress file.

If baseline verification is already failing, fix that first. Do not stack new feature work on top of a broken starting state.

## Working Rules

- Work on one feature at a time.
- Do not mark a feature complete just because code was added.
- Keep changes within the selected feature scope. If a blocker seems to require a supporting fix outside that scope, stop and ask a human to validate the fix before making it.
- Do not silently change verification rules during implementation.
- Prefer durable repo artifacts over chat summaries.

## Required Artifacts

State files live in a state folder that depends on what is being worked on:

- `harness/state/` when working on the Joy coding agent itself.
- `harness/state/<worked-on-application>/` when working on a target application, where `<worked-on-application>` is the application's folder name (for example `harness/state/note-taker/` for `examples/note-taker`).

That folder holds:

- `PROGRESS.md`, the progress file: session log and current verified status.
- `DECISIONS.md`, the decisions file: one short memo per important design decision, giving what was decided, why, and when (a date). It is not a design document. Record a decision when it shapes how later work should be done, such as an interface or format choice, a trade-off, or a rule a human set.
- `session-handoff.md`, the handoff file: optional compact handoff for larger sessions (see Handoff File).

Both `PROGRESS.md` and `DECISIONS.md` are running summaries, not append-only logs. When one gets bloated, or fills up with entries that matter little to the task at hand, condense it:

- In `PROGRESS.md`, merge or shorten older session entries and drop details the code or git history already records. Always keep the current verified state, the next step, open risks and blockers, and the full test and verification evidence for the current task.
- In `DECISIONS.md`, merge related decisions, and when a decision is replaced, reverted or no longer applies, replace it with its successor or remove it. Keeping a one-line note of why the old choice was dropped is fine. Always keep every decision that still governs the code.

### Handoff File

The handoff file must let a fresh session restore the project state from it alone. It is a snapshot of where the last session ended, rewritten at each clock out, not a log. It has four sections of a few lines each:

1. **Repo state**: the commit the work builds on (`git rev-parse --short HEAD`) and where the work sits. Work is not always committed: when it is left in the staging area for a human to review, say so and list the staged files. Also list any unstaged or untracked files that are not part of the work, so the next session leaves them alone.
2. **Runtime state**: the verification command that ran, when, and its result as counts (for example `uv run pytest`: 42 passed, 0 failed), not just "tests pass".
3. **Blockers**: anything stopping progress, including decisions waiting on a human. Write "None" when there are none.
4. **Next actions**: ordered, concrete steps. The first one is where the next session starts.

When restoring from the handoff file leaves something ambiguous, record the ambiguity in the progress file so a human can improve this template.

## Definition Of Done

A task is done only when all of the following are true:

1. The target behavior is implemented.
2. The application's tests pass locally.
3. The application's verification checks pass.
4. The progress file records the task in its session log, with evidence that the tests and verification checks actually ran and passed.
5. The repository remains restartable from the clock-in routine (see Session Start).

The tests and verification checks depend on the application being worked on. When that is an application other than the Joy coding agent itself (for example `examples/note-taker`), use the commands that application's documentation explicitly gives (its `README.md`, `ARCHITECTURE.md` or `AGENTS.md`, or existing pieces of `*.md` documentation that exist within the project). Do not guess or invent commands. If the documentation names none, say so in the progress file and ask a human how the work should be verified.

Tracking features and their state is the responsibility of the humans developing the application, not of the coding agent: do not create or update a features list.

## Session End (Clock Out)

Before ending a session:

1. Run the application's verification check again (the same documented command as at clock in) to confirm the repo is in a consistent state.
2. Update the progress file, including the result of that check, and record any new design decision in the decisions file, condensing either one first if it has grown bloated (see Required Artifacts). For a larger session, also rewrite the handoff file (see Handoff File).
3. Record any unresolved risk or blocker.
4. Add to git staging area modified files with a descriptive message once the work is in a safe state _then_ ask for a human to review the work.
5. Leave the repo clean enough for the next session to run using the clock-in routine.
