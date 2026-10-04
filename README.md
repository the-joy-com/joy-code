# Joy Code

Joy Code is a wannabee clone of [Claude Code](https://claude.com/claude-code), built using the contents of [Hands-On Harness Engineering](https://hands-on-harness-engineering.com/) as a starter, but in Python instead of Node.

## Bootstrap

On a fresh clone, and at the start of every coding-agent session, run:

```bash
./init.sh
```

It installs the locked dependencies and checks that Joy can start and be tested. See [`BOOTSTRAP.md`](BOOTSTRAP.md) for its contract and exit codes.

## Running the CLI

The CLI lives in the `cli` folder and is managed with [uv](https://docs.astral.sh/uv/).

### Dev mode

Run the CLI from source:

```bash
cd cli && uv run joy --help
```

### Prod mode

Build a standalone executable with [PyInstaller](https://pyinstaller.org/) into the root `bin` folder (intermediate build files go in `cli/build`):

```bash
cd cli && uv run pyinstaller --onefile --copy-metadata joy --name joy --distpath ../bin --workpath build --specpath build joy.py
```

Then run the executable (no Python or uv needed):

```bash
./bin/joy --help
```

The executable only runs on the OS and CPU architecture it was built on.

## Testing

Tests use [pytest](https://docs.pytest.org/), a uv dev dependency. Run the suite from the `cli` folder:

```bash
cd cli && uv run pytest
```

This is Joy's verification check. For now `cli/test_suite.py` only proves the suite runs.

## Harness

The `harness` folder holds the harness we use to develop the coding agent.

[`AGENTS.md`](AGENTS.md) holds the rules coding agents follow in this repository: the startup workflow, the working rules, the progress files, the definition of done and the end-of-session steps.

### Task ledger

Each state folder under `harness/state/` holds a `tasks.json` ledger that enforces the WIP limit, 1 by default (see [`AGENTS.md`](AGENTS.md)). Manage it from the repository root with:

```bash
uv run --locked --project cli joy task --help
```

`joy task activate` refuses to start a task while the Verified Completion Rate (passing tasks / activated tasks) is below 1.0, and only `joy task pass`, which runs the ledger's bootstrap script and records the evidence, marks a task `passing`. Finished tasks move to `tasks.archive.jsonl`, so the ledger stays the size of the open work. Only a human can drop a task (`joy task drop` asks to type the task id in an interactive terminal) or change the WIP limit, 1 by default (`joy task wip <n>` asks to type the new limit there).

### Tasks

`harness/instructions` holds the task specifications for the instructions subsystem. Each task is a numbered Markdown file (`1.md`, `2.md`, ...) with two sections:

- **TASK**: what to build.
- **DONE WHEN**: the commands to run, and what they must output, before the task counts as complete.

## Examples

The `examples` folder is meant to hold example applications built with the Joy coding agent and its harness.
