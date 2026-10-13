"""Command-line entry point: `d3soccer <command>`."""

import argparse

from d3soccer import __version__, storage


def cmd_init_db(args: argparse.Namespace) -> None:
    storage.connect().close()
    print("Database ready.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="d3soccer", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    init_db = sub.add_parser("init-db", help="create the local SQLite database")
    init_db.set_defaults(func=cmd_init_db)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
