import json
import sys
from importlib.metadata import version


def main() -> None:
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print("joy - a tiny coding agent")
        print("")
        print("Usage:")
        print("  joy --help            Print this help.")
        print("  joy version [--json]  Print the version.")
        sys.exit(0)

    if args == ["version"]:
        print(version("joy"))
        sys.exit(0)

    if args == ["version", "--json"]:
        print(json.dumps({"version": version("joy")}))
        sys.exit(0)

    print(f"unknown command: {' '.join(args)}", file=sys.stderr)
    sys.exit(2)
