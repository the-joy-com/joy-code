import asyncio
import json
import sys
from importlib.metadata import version

from commands.ask import run_ask
from commands.import_ import run_import
from commands.index import run_index
from commands.status import run_status

HELP = """note-taker - a tiny note-taking app

Usage:
  note-taker import <dir>       Walk <dir>, ingest .md files into tmp/.note-taker/notes.json
  note-taker index              Build tmp/.note-taker/index.json from current notes
  note-taker ask <query> [-k N] Print the top N (default 3) notes matching <query>, with citations.
                                Words after `--` are always query words, even if they
                                look like an option: `ask -k 2 -- -k` searches for "-k".
  note-taker status              Print the note count and the path of notes.json.
  note-taker version [--json]   Print the version.
  note-taker --help             Print this help.
"""


def main() -> None:
    args = sys.argv[1:]
    cmd, rest = (args[0], args[1:]) if args else (None, [])

    # sys.exit raises SystemExit, which `except Exception` doesn't catch,
    # just like process.exit isn't caught in JavaScript.
    try:
        match cmd:
            case None | "--help" | "-h":
                print(HELP)
                sys.exit(0)
            case "import":
                if not rest:
                    print("import requires a directory", file=sys.stderr)
                    sys.exit(2)
                sys.exit(asyncio.run(run_import(rest[0])))
            case "index":
                sys.exit(asyncio.run(run_index()))
            case "ask":
                # The first `--` ends the options: everything after it is a query word,
                # so a query can hold words that look like options, such as `-k`.
                sep = rest.index("--") if "--" in rest else len(rest)
                words, literal, k = list(rest[:sep]), rest[sep + 1 :], 3
                if "-k" in words:
                    i = words.index("-k")
                    value = words[i + 1] if i + 1 < len(words) else ""
                    if not (value.isdigit() and int(value) > 0):
                        print("-k requires a positive integer", file=sys.stderr)
                        sys.exit(2)
                    k = int(value)
                    del words[i : i + 2]
                words += literal
                if not words:
                    print("ask requires a query", file=sys.stderr)
                    sys.exit(2)
                # Unquoted words are joined, so `ask python async` works like `ask "python async"`.
                sys.exit(asyncio.run(run_ask(" ".join(words), k)))
            case "status" if rest == []:
                sys.exit(asyncio.run(run_status()))
            case "version" if rest == []:
                print(version("note-taker"))
                sys.exit(0)
            case "version" if rest == ["--json"]:
                print(json.dumps({"version": version("note-taker")}))
                sys.exit(0)
            case _:
                print(f"unknown command: {' '.join(args)}", file=sys.stderr)
                sys.exit(2)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
