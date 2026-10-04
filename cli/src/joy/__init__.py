import sys


def main() -> None:
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print("joy - a tiny coding agent")
        print("")
        print("Usage:")
        print("  joy --help        Print this help.")
        sys.exit(0)

    print(f"unknown command: {' '.join(args)}", file=sys.stderr)
    sys.exit(2)
