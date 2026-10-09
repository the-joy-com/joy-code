# Instruction template

Every task in a Joy task ledger starts from a spec based on this template. Copy everything below the line into a draft in the drafts folder: `harness/instructions/drafts/<name>.md` for the Joy coding agent itself, `harness/instructions/<worked-on-application>/drafts/<name>.md` for a target application (for example `harness/instructions/note-taker/drafts/`). Replace every `<...>` placeholder and keep the sections in this order. Then ask a human to approve it, from the repository root:

```bash
uv run --locked --project cli joy task add --spec harness/instructions/drafts/<name>.md --state harness/state
```

`joy task add` checks the draft and shows it, asks the human to type the new task id (for example `T-3`) at an interactive terminal, then runs the verification command, which must fail. Only then does it add the task to the ledger, write the spec to `harness/instructions/<id>.md` (`harness/instructions/<application>/<id>.md` for a target application) and delete the draft. From then on, TASK, SCOPE and DONE WHEN are frozen: `joy task activate` and `joy task pass` refuse to run if they changed, and `joy task pass` refuses work that changed a file SCOPE does not list. `joy task` writes STATE and EVIDENCE itself.

---

# <short task title>

## TASK

<The target behavior, described from the outside: the exact command or call a user or caller runs, what they observe (output, files, limits such as "at most 3 results"), and the exit code. One behavior per spec: if there are two, write two specs.>

## SCOPE

Files and folders this task is expected to change:

- `<path>`
- `<path to the test file>`

Start each item with a path in backticks, relative to the repository root; a path ending in `/` is a folder and covers every file under it. `joy task pass` refuses work that changed any other file since the task was activated (gitignored files do not count). Needing to change anything else means the task is wrong or out of scope: write a new draft for it, or block this task and ask a human (see `AGENTS.md`).

## DONE WHEN

The task is done only when all of the following are true:

1. The behavior described in **TASK** is implemented, within **SCOPE**.
2. The verification command below, which failed when the spec was approved, now exits 0.
3. The application's own tests and verification checks pass (see the Definition Of Done in `AGENTS.md`).
4. `joy task pass` marked the task `passing`: it runs the bootstrap script and this verification command, and needs both to exit 0.

The verification command runs from the repository root. It decides pass or fail by its exit code alone (0 when the behavior is there, non-zero when it is missing or wrong), sets up any data it needs so it runs the same from a fresh clone, and must fail before the work starts: a check that already passes, or that a wrong result can satisfy, proves nothing. Keep it to exactly one `bash` block in this section.

```bash
<command that checks this behavior and only this behavior>
```

## STATE

Leave empty: `joy task` writes it.

## EVIDENCE

Leave empty: `joy task` writes the verification command's output when the spec was approved (Before) and when the task passed (After).
