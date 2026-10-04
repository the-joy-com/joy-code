# Note Taker

Note Taker is an example application used to illustrate what the Joy coding agent and its harness can produce.

## Running the CLI

The CLI lives in this folder and is managed with [uv](https://docs.astral.sh/uv/).

### Dev mode

Run the CLI from source (from this folder):

```bash
uv run note-taker --help
```

### Prod mode

Build a standalone executable with [PyInstaller](https://pyinstaller.org/) into the repository root `bin` folder (intermediate build files go in `examples/note-taker/build`), from this folder:

```bash
uv run pyinstaller --onefile --copy-metadata note-taker --name note-taker --distpath ../../bin --workpath build --specpath build cli.py
```

Then run the executable from the repository root (no Python or uv needed):

```bash
./bin/note-taker --help
```

The executable only runs on the OS and CPU architecture it was built on.

## Store

Notes are stored as JSON files in `<repo>/tmp/.note-taker`, created on the first write, whatever the working directory and whether the CLI runs from source or as the built binary (which expects to live in `<repo>/bin`).

## Commands

- `note-taker --help`: print the help.
- `note-taker import <dir>`: walk `<dir>` and ingest its `.md` files into `notes.json`.
- `note-taker index`: build `index.json` from the current notes.
- `note-taker version [--json]`: print the version, as plain text or as `{"version": "<v>"}`.
