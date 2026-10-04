# Bootstrap

`./init.sh` (in this folder) is the only supported way to bring a fresh clone of note-taker to a verified start. Run it from anywhere; it works from this folder. It is idempotent: it installs dependencies from `uv.lock` without rewriting it, so a second run changes nothing and `git status` stays clean. It needs [uv](https://docs.astral.sh/uv/) and should finish in under three minutes.

## Contract

After `./init.sh` exits 0, the repository satisfies all four:

| Property            | Probe                                                                             |
|---------------------|-----------------------------------------------------------------------------------|
| can-start           | `uv run --locked note-taker --help` exits 0                                       |
| can-test            | `uv run --locked pytest` exits 0                                                  |
| can-see-progress    | `<repo>/harness/state/note-taker/PROGRESS.md` exists with a `## ... next step` heading |
| can-pick-next-steps | `README.md` and `ARCHITECTURE.md` exist in this folder                            |

The can-see-progress probe is the only one that reads the coding-agent harness; the app's code and tests never do. can-pick-next-steps relies on the app's own docs, which say how to run, test and extend it. `harness/state/` is not committed, so on a fresh clone `init.sh` creates a skeleton `PROGRESS.md` whose next step is to ask a human. An existing one is never touched.

Failure exit codes: 10 = install (`uv sync --locked` failed or rewrote `uv.lock`), 11 = can-start, 12 = can-test, 13 = can-see-progress, 14 = can-pick-next-steps.

## Updating

When you add a new initialization step, add it to `init.sh` and update this contract table if it introduces a new property. A dependency change goes through `uv add` / `uv lock` and a committed `uv.lock`, never through `init.sh`.
