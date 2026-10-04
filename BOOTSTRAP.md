# Bootstrap

`./init.sh` is the only supported way to bring a fresh clone of the Joy coding agent to a verified start. Run it from anywhere; it works from the repository root. It is idempotent: it installs dependencies from `cli/uv.lock` without rewriting it, so a second run changes nothing and `git status` stays clean. It needs [uv](https://docs.astral.sh/uv/) and should finish in under three minutes.

It only bootstraps Joy itself. Each target application has its own `init.sh` and `BOOTSTRAP.md` (for example `examples/note-taker/`).

## Contract

After `./init.sh` exits 0, the repository satisfies all four:

| Property            | Probe                                                                 |
|---------------------|-----------------------------------------------------------------------|
| can-start           | `uv run --locked --project cli joy --help` exits 0                    |
| can-test            | `uv run --locked --project cli pytest cli` exits 0                    |
| can-see-progress    | `harness/state/PROGRESS.md` exists with a `## ... next step` heading, and `joy task status --state harness/state` exits 0 (`harness/state/tasks.json` is a valid ledger) |
| can-pick-next-steps | `AGENTS.md` exists                                                    |

`harness/state/` is not committed, so on a fresh clone `init.sh` creates a skeleton `PROGRESS.md` whose next step is to ask a human, and an empty `tasks.json` ledger whose bootstrap is `./init.sh` (finished tasks later move to `tasks.archive.jsonl`). Existing ones are never touched. A clock in does not fail because a task is `active` or `blocked`: resuming it is normal, and the WIP=1 gate sits in `joy task activate`.

Failure exit codes: 10 = install (`uv sync --locked` failed or rewrote `cli/uv.lock`), 11 = can-start, 12 = can-test, 13 = can-see-progress, 14 = can-pick-next-steps.

## Updating

When you add a new initialization step, add it to `init.sh` and update this contract table if it introduces a new property. A dependency change goes through `uv add` / `uv lock` and a committed `cli/uv.lock`, never through `init.sh`.
