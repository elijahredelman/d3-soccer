"""Command-line entry point: `d3soccer <command>`."""

import argparse

from d3soccer import __version__


def cmd_scrape(args: argparse.Namespace) -> None:
    from d3soccer.pipelines import conferences, national

    # National first: it is quick, and keeps scores current even if the long
    # conference pull fails partway.
    if args.job in ("national", "all"):
        national.run()
    if args.job in ("conferences", "all"):
        conferences.run(args.only or None)


def cmd_build(args: argparse.Namespace) -> None:
    from d3soccer.pipelines import app_data

    app_data.run()


def cmd_probe(args: argparse.Namespace) -> None:
    from d3soccer.pipelines import probe

    probe.run(args.urls, failed=args.failed, links=args.links, dump=args.dump)


def cmd_serve(args: argparse.Namespace) -> None:
    import functools
    import http.server

    from d3soccer.config import WEB_DIR

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=WEB_DIR)
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Serving {WEB_DIR} at http://127.0.0.1:{args.port}/")
        server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="d3soccer", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scrape = sub.add_parser("scrape", help="pull live data and write a dated snapshot")
    scrape.add_argument("job", choices=["national", "conferences", "all"])
    scrape.add_argument(
        "only", nargs="*", help="conference keys to pull (default: all), e.g. SCIAC NESCAC"
    )
    scrape.set_defaults(func=cmd_scrape)

    build = sub.add_parser("build", help="regenerate web/app_data.js from the latest snapshots")
    build.set_defaults(func=cmd_build)

    probe = sub.add_parser("probe", help="fetch pages and describe their markup, to fix parsers")
    probe.add_argument("urls", nargs="*")
    probe.add_argument(
        "--failed", action="store_true", help="probe every non-403 failure in the latest snapshot"
    )
    probe.add_argument("--links", help="also list hrefs containing this text")
    probe.add_argument(
        "--dump", action="append", help="print the HTML of the first match of this CSS selector"
    )
    probe.set_defaults(func=cmd_probe)

    serve = sub.add_parser("serve", help="serve the web/ site locally")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
