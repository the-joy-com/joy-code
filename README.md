# Joy Code

Joy Code is a wannabee clone of [Claude Code](https://claude.com/claude-code), built using the contents of [Hands-On Harness Engineering](https://hands-on-harness-engineering.com/) as a starter, but in Python instead of Node.

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

## Harness

The `harness` folder holds the harness we use to develop the coding agent.

[`AGENTS.md`](AGENTS.md) holds the rules coding agents follow in this repository: the startup workflow, the working rules, the progress files, the definition of done and the end-of-session steps.

### Tasks

`harness/instructions` holds the task specifications for the instructions subsystem. Each task is a numbered Markdown file (`1.md`, `2.md`, ...) with two sections:

- **TASK**: what to build.
- **DONE WHEN**: the commands to run, and what they must output, before the task counts as complete.

## Examples

The `examples` folder is meant to hold example applications built with the Joy coding agent and its harness.
