"""Module for command line interface."""

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

import orjson

from .info import __issues__, __project__, __summary__, __version__
from .jumplist import parse_jumplist
from .log import setup_logging

LOG_LEVELS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


logger = logging.getLogger(__name__)


class HelpArgumentParser(argparse.ArgumentParser):
    """Parser for show usage on error."""

    def error(self, message: str) -> NoReturn:  # pragma: no cover
        """Handle error from argparse.ArgumentParser."""
        self.print_help(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def get_parser() -> argparse.ArgumentParser:
    """Prepare ArgumentParser."""
    parser = HelpArgumentParser(
        prog="jumplist-parser",
        description=__summary__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s, version {__version__}",
    )
    parser.add_argument(
        "--log-level",
        metavar="level",
        default="INFO",
        choices=LOG_LEVELS,
        help=(
            "print log messages of this level and higher, "
            "possible choices: %(choices)s"
        ),
    )
    parser.add_argument(
        "--log-file",
        metavar="file",
        help="log file to store DEBUG level messages",
    )
    parser.add_argument(
        "--split-by-lnk",
        action="store_true",
        help="Each jumplist will output as many JSON objects as "
        "it contains LNK in it, instead of one per file.",
    )
    parser.add_argument(
        "--ignore-empty",
        action="store_true",
        help="Skip empty jumplist.",
    )
    parser.add_argument(
        "filenames",
        metavar="filenames",
        nargs="+",
        help="Path to file",
    )
    return parser


def print_json(value: Any) -> None:
    """Display json with newline on stdout using UTF-8."""
    sys.stdout.write(
        orjson.dumps(
            value,
            option=orjson.OPT_APPEND_NEWLINE,
        ).decode("utf-8"),
    )


def entrypoint(argv: Sequence[str] | None = None) -> None:
    """Entrypoint for command line interface."""
    try:
        parser = get_parser()
        args = parser.parse_args(argv)
        setup_logging(args.log_file, args.log_level)
        logger.info("jumplist-parser, version %s", __version__)
        for filename in args.filenames:
            path = Path(filename).resolve()
            with path.open("rb") as file:
                jumplist = parse_jumplist(file, path)
            if args.split_by_lnk:
                links = jumplist.pop("lnk")  # type: ignore[misc]
                if links:
                    for lnk in links:
                        print_json({**jumplist, "lnk": lnk})
                elif not args.ignore_empty:
                    print_json(jumplist)
            elif jumplist["lnk"] or not args.ignore_empty:
                print_json(jumplist)
    except Exception as err:  # NoQA: BLE001  # pragma: no cover
        logger.critical(
            "Unexpected error (%s, version %s)",
            __project__,
            __version__,
            exc_info=err,
        )
        logger.critical(
            "Please, report this error and previous logs to %s.",
            __issues__,
        )
        sys.exit(1)
