"""Command-line entry point: `d3soccer <command>`."""

import argparse
import importlib

from d3soccer import __version__

# `d3soccer scrape <job>` -> module in d3soccer.pipelines with a run() function.
SCRAPE_JOBS = {
    "sciac": "sciac",
    "batch1": "conferences_batch1",
    "batch2": "conferences_batch2",
    "batch3": "conferences_batch3",
    "leaders": "leaders",
}


def run_pipeline(module: str) -> None:
    importlib.import_module(f"d3soccer.pipelines.{module}").run()


def cmd_scrape(args: argparse.Namespace) -> None:
    jobs = list(SCRAPE_JOBS) if args.job == "all" else [args.job]
    for job in jobs:
        print(f"== scrape {job} ==")
        run_pipeline(SCRAPE_JOBS[job])


def cmd_build(args: argparse.Namespace) -> None:
    run_pipeline("app_data")


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
    scrape.add_argument("job", choices=[*SCRAPE_JOBS, "all"])
    scrape.set_defaults(func=cmd_scrape)

    build = sub.add_parser("build", help="regenerate web/app_data.js from the latest snapshots")
    build.set_defaults(func=cmd_build)

    serve = sub.add_parser("serve", help="serve the web/ site locally")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
