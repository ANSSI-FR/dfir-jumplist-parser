"""Module for logging in CLI."""

import logging
import sys
import warnings
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from typing import IO, Protocol, TextIO, TypeVar

from .resolver import PathStr
from .utils import get_name

CONTEXT_PATH: ContextVar[str | None] = ContextVar("log_path", default=None)
DEFAULT_ATTRS = logging.LogRecord(
    "dummy",
    logging.CRITICAL,
    "dummy",
    42,
    None,
    None,
    None,
).__dict__.keys()
logger = logging.getLogger(__name__)


class ExtraFormatter(logging.Formatter):  # pragma: no cover
    """Class providing support for context logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format with extra information."""
        path = CONTEXT_PATH.get()
        if path is not None:
            record.path = path
        extras = set(record.__dict__.keys()) - DEFAULT_ATTRS
        fmt = self._fmt
        if fmt is not None:
            for attr in extras:
                fmt += f" {attr}=%({attr})r"
            self._style._fmt = fmt  # noqa: SLF001
        return super().format(record)


def showwarning(  # pragma: no cover
    message: Warning | str,
    category: type[Warning],
    filename: str,
    lineno: int,
    file: TextIO | None = None,  # noqa: ARG001
    line: str | None = None,  # noqa: ARG001
) -> None:
    """Show warning within the logger."""
    for module_name, module in sys.modules.items():  # noqa: B007
        module_path = getattr(module, "__file__", None)
        if module_path and Path(module_path).samefile(filename):
            break
    else:
        module_name = Path(filename).stem
    msg = f"{category.__name__}: {message}"
    logger = logging.getLogger(module_name)
    try:
        _, _, func, info = logger.findCaller()
    except ValueError:  # pragma: no cover
        func, info = "(unknown function)", None
    record = logger.makeRecord(
        logger.name,
        logging.WARNING,
        filename,
        lineno,
        msg,
        (),
        None,
        func,
        None,
        info,
    )
    logger.handle(record)


def setup_logging(  # pragma: no cover
    log_file: str | None = None,
    log_level: str | None = None,
) -> None:
    """Do setup logging to redirect to log_file at DEBUG level."""
    if log_level is None:
        log_level = "INFO"

    if log_level == "DEBUG":
        log_format = "[%(asctime)s] [jumplist-parser] %(levelname)-8s - %(name)s - %(message)s"  # noqa: E501
    else:
        log_format = (
            "[%(asctime)s] [jumplist-parser] %(levelname)-8s - %(message)s"
        )
    # Setup logging
    if log_file:
        # Send everything (DEBUG included) in the log file
        # and keep only log_level messages on the console
        logging.basicConfig(
            level=logging.DEBUG,
            format=log_format,
            filename=log_file,
            filemode="w",
        )
        # define a Handler which writes messages of log_level
        # or higher to the sys.stderr
        console = logging.StreamHandler()
        console.setLevel(log_level)
        # set a format which is simpler for console use
        formatter = logging.Formatter(log_format)
        # tell the handler to use this format
        console.setFormatter(formatter)
        # add the handler to the root logger
        logging.root.addHandler(console)
    else:
        logging.basicConfig(level=log_level, format=log_format)
    warnings.showwarning = showwarning
    for handler in logging.root.handlers:
        handler.setFormatter(ExtraFormatter(handler.formatter._fmt))  # type: ignore[union-attr]  # noqa: SLF001


T_co = TypeVar("T_co", covariant=True)
R = TypeVar("R")


class ParserProtocol(Protocol[T_co]):
    """Base protocol for jumpllist parser functions."""

    def __call__(
        self,
        file_obj: IO[bytes],
        path: PathStr | None = None,
    ) -> T_co:
        """Called function."""


def set_context_path(func: ParserProtocol[R]) -> ParserProtocol[R]:
    """Set context path and remove it once the function is terminated."""

    @wraps(func)
    def wrapper(file_obj: IO[bytes], path: PathStr | None = None) -> R:
        if CONTEXT_PATH.get() is None:
            CONTEXT_PATH.set(get_name(file_obj, path))
            logger.debug("Parsing")
            if path is None:
                logger.debug("Missing path, AppID can be inexact")
            try:
                result = func(file_obj, path)
            finally:
                CONTEXT_PATH.set(None)
        else:
            result = func(file_obj, path)
        return result

    return wrapper
