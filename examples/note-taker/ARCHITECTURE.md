# Architecture

`note-taker` is a single Python 3.12+ CLI, managed with uv, that ingests markdown
notes, builds a token index, and answers keyword queries from it. It has no
runtime dependencies beyond the standard library.

## Layout

- `cli.py` — argv dispatcher and `note-taker` entry point (`cli:main`); the only file that calls `sys.exit`. It parses options by hand; a `--` argument ends a command's options, so every argument after it is passed on as plain input (today only `ask` takes options and free-form words).
- `commands/<verb>.py` — one module per CLI verb, exports an async `run_<verb>(...)` that returns an exit code (`import_.py` carries a trailing underscore because `import` is a keyword).
- `store/types.py` — `TypedDict` schemas for on-disk state.
- `store/io.py` — read/write helpers for the `.note-taker/*.json` store.
- `test_e2e.py` — end-to-end tests that run `cli.py` in a subprocess against a throwaway store.
- `commands/test_<verb>.py` — unit tests for a command, next to it.
- `<repo>/tmp/.note-taker/` — local state directory, resolved from the source location (or from the built binary in `<repo>/bin`), never from the working directory; never committed.

## Data flow

```
markdown files            notes.json                       index.json
      │                        │                                │
      ▼                        ▼                                ▼
note-taker import ───► notes (id,path,title,body,imported_at) ──► note-taker index ──► tokens
                                                                                          │
                                                                                          ▼
                                                                                  note-taker ask
```

## Boundaries

- `commands/*` may import from `store/*`, never the other way around.
- Only `cli.py` is allowed to call `sys.exit`. Everything else returns an exit
  code as an `int`; `cli.py` turns uncaught exceptions into exit code 1.
- All reads and writes of the store go through `store/io.py`. No store paths or
  JSON (de)serialization scattered through command files.
- Blocking file I/O runs in a thread with `asyncio.to_thread`, since the standard
  library has no async file API.
