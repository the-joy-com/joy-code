import asyncio
import json
import sys
from importlib.metadata import version

from commands.import_ import run_import
from commands.index import run_index

HELP = """note-taker - a tiny note-taking app

Usage:
  note-taker import <dir>       Walk <dir>, ingest .md files into tmp/.note-taker/notes.json
  note-taker index              Build tmp/.note-taker/index.json from current notes
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
