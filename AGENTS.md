# AGENTS.md

This repository is designed for long-running coding-agent work. The goal is not to maximize raw code output. The goal is to leave the repo in a state where the next session can continue without guessing.

## Session Start (Clock In)

Before writing code:

1. Confirm the working directory with `pwd`.
2. Run the bootstrap script of what is being worked on, always, whether it is the Joy coding agent itself (`./init.sh`, contract in [`BOOTSTRAP.md`](BOOTSTRAP.md)) or a target application (its own `init.sh`, for example `examples/note-taker/init.sh`, contract in its `BOOTSTRAP.md`). It installs the locked dependencies and checks that the project can start, can test, can see progress and can pick up next steps. A non-zero exit code names the broken property (see the matching `BOOTSTRAP.md`). If the application has no `init.sh`, say so in the progress file and ask a human how to bootstrap it.
3. Read the handoff file if there is one, then the progress file and `joy task status` (see Required Artifacts), for the latest verified state, the active task and the next step.
4. Read the decisions file for the design decisions that still govern the code.
5. Review recent commits with `git log --oneline -5`.
6. Continue from the next step recorded in the progress file.

If the bootstrap or the baseline verification is already failing, fix that first. Do not stack new feature work on top of a broken starting state.

## Working Rules

- WIP=n: run `joy task status` before any work. It shows the WIP limit `n` (1 unless a human raised it) and the tasks in progress, that is `active` or `blocked`. While `n` tasks are in progress, finish one (`joy task pass`) before activating another, or, if it is stuck, block it with a documented reason (see below) and ask a human: a `blocked` task still counts toward the limit, so blocking does not free a slot. Tasks live in the task ledger (see Required Artifacts) as `not_started`, `active`, `blocked`, `passing` or `dropped`. Only a human may change `n`, with `joy task wip <n>`, which asks to type the new limit at an interactive terminal: do not run it or work around that confirmation. Change the ledger only through `joy task` (`uv run --locked --project cli joy task --help`, run from the repository root, with `--state` pointing at the state folder).
- Never edit a harness task JSON file directly: not `tasks.json`, not `tasks.archive.jsonl`, in no state folder, and by no means (editor, file-writing tool, shell redirection, `sed`, a script). If the ledger is invalid or looks wrong, stop and ask a human instead of repairing it.
- Split the work into tasks with `joy task add`. `joy task activate` refuses to start a task while the Verified Completion Rate (passing tasks / activated tasks, `dropped` excluded) is below 1.0, so the next task only starts once the active one is `passing` (with a higher WIP limit, once fewer tasks than the limit are `active` or `blocked`). Only `joy task pass` marks a task `passing`: it runs the bootstrap script and records the evidence, and refuses when that script fails. Do not mark a task complete just because code was added.
- If the active task is `blocked`, record the blocker with `joy task block <id> --reason "..."` and in the progress file, then ask a human. Do not pick up another task in the meantime. Only a human may drop a task: `joy task drop` asks to type the task id at an interactive terminal, so do not try to run it or work around that confirmation; ask a human.
- Start every implementation with a failing test: write a test for the target behavior, run it and see it fail for the expected reason, then write the code that makes it pass. A test that has never failed proves nothing.
- Keep changes within the active task's scope. Do not "also" refactor, fix or improve something else along the way: add it as a `not_started` task instead. If the added tasks start to look like scope creep, or a blocker seems to require a supporting fix outside that scope, block the active task and ask a human to validate before going on.
- Do not silently change verification rules during implementation.
- Prefer durable repo artifacts over chat summaries.

## Required Artifacts

State files live in a state folder that depends on what is being worked on:

- `harness/state/` when working on the Joy coding agent itself.
- `harness/state/<worked-on-application>/` when working on a target application, where `<worked-on-application>` is the application's folder name (for example `harness/state/note-taker/` for `examples/note-taker`).

That folder holds:

- `PROGRESS.md`, the progress file: session log and current verified status.
- `tasks.json`, the task ledger: the machine-readable state of each task and the evidence that it passed, managed with `joy task`. It only holds open tasks: `passing` and `dropped` ones move to the append-only `tasks.archive.jsonl` next to it, and only their counts stay. Read the ledger through `joy task status` (add `--json` for a compact machine-readable view), never by opening `tasks.json`, and do not read the archive unless a human asks for task history. Joy's `init.sh` creates and checks its own. For a target application, create it once with `joy task init --state harness/state/<worked-on-application> --bootstrap <path to its init.sh>`.
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
4. `joy task pass` marked the task `passing` in the task ledger, and the progress file records the task in its session log.
5. The repository remains restartable from the clock-in routine (see Session Start).

The tests and verification checks depend on the application being worked on. For the Joy coding agent itself, it is `uv run pytest` in `cli/`, as its `README.md` documents. When that is an application other than the Joy coding agent itself (for example `examples/note-taker`), use the commands that application's documentation explicitly gives (its `README.md`, `ARCHITECTURE.md` or `AGENTS.md`, or existing pieces of `*.md` documentation that exist within the project). Do not guess or invent commands. If the documentation names none, say so in the progress file and ask a human how the work should be verified.

Tracking features and their state is the responsibility of the humans developing the application, not of the coding agent: do not create or update a features list.

## Session End (Clock Out)

Before ending a session:

1. Run the application's verification check again (the same documented command the bootstrap script runs at clock in) to confirm the repo is in a consistent state.
2. Update the progress file, including the result of that check, and record any new design decision in the decisions file, condensing either one first if it has grown bloated (see Required Artifacts). For a larger session, also rewrite the handoff file (see Handoff File).
3. Record any unresolved risk or blocker.
4. Add to git staging area modified files with a descriptive message once the work is in a safe state _then_ ask for a human to review the work.
5. Leave the repo clean enough for the next session to run using the clock-in routine.
