# Note Taker

Note Taker is an example application used to illustrate what the Joy coding agent and its harness can produce.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for its layout, data flow and module boundaries.

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

## Testing

Tests use [pytest](https://docs.pytest.org/) with [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) for the async commands. Both are uv dev dependencies, so `uv run` installs them. Run the whole suite from this folder:

```bash
uv run pytest
```

This is the app's verification check: a change is verified when the whole suite passes.

- Unit tests sit next to the command they cover, as `commands/test_<verb>.py`. They call `run_<verb>(...)` directly, marked with `@pytest.mark.asyncio`, and use `monkeypatch` to point `store.io.DIR` at `<repo>/tmp/.note-taker-tests`.
- End-to-end tests live in `test_e2e.py`. They copy the app into a `tmp_path` laid out like the repo and run `cli.py` in a subprocess, checking stdout, exit codes and the JSON files written.

None of the tests touch the real store in `<repo>/tmp/.note-taker`.

## Store

Notes are stored as JSON files in `<repo>/tmp/.note-taker`, created on the first write, whatever the working directory and whether the CLI runs from source or as the built binary (which expects to live in `<repo>/bin`).

## Commands

- `note-taker --help`: print the help.
- `note-taker import <dir>`: walk `<dir>` and ingest its `.md` files into `notes.json`.
- `note-taker index`: build `index.json` from the current notes.
- `note-taker ask <query> [-k N]`: print the top `N` notes (default 3) matching the most distinct words of `<query>`, each with its first non-blank, non-heading line and its source path. `-k` can go before or after the query words. Needs `index` to have run.
  - Everything after `--` is a query word, even if it looks like an option: `note-taker ask -k 2 -- -k` searches for `-k` instead of reading it as the option. Only the first `--` counts; a later one is a query word too.
  - Query words are split like the index: only runs of 3 or more letters or digits are kept, and common words such as `the` are dropped. A query made only of shorter words or punctuation (like `-k` itself) prints `no matches`.
- `note-taker version [--json]`: print the version, as plain text or as `{"version": "<v>"}`.
