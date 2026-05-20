"""Utils functions for testing."""

import sys
import traceback
from collections.abc import Callable
from multiprocessing import Process, Queue
from pathlib import Path
from typing import (
    Any,
    TypeVar,
)

from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T")


def _worker_as_daemon(
    *args: Any,
    __func: Callable[..., Any],
    __queue: "Queue[Any]",
    **kwargs: Any,
) -> None:
    try:
        __queue.put(__func(*args, **kwargs))
    except Exception:  # noqa: BLE001
        exc_type, exc_value, tb = sys.exc_info()
        tb_str = traceback.format_exception(exc_type, exc_value, tb)
        __queue.put(WorkerError("Worker Error:\n" + "".join(tb_str).strip()))


class WorkerError(Exception):
    """Exception from worker."""


def run_as_daemon(
    func: Callable[P, T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    """Run a function in a daemon."""
    # For communication with process
    queue: "Queue[T]" = Queue()  # noqa: UP037
    kwargs["__queue"] = queue
    # Use a param for transfer function
    kwargs["__func"] = func
    try:
        # Mark the process as daemon
        p = Process(
            target=_worker_as_daemon,
            args=args,
            kwargs=kwargs,
            daemon=True,
        )
        # Start the process
        p.start()
        # Wait the end of the process and clean up
        p.join()
        # Get the result or the error
        obj = queue.get()
        if isinstance(obj, WorkerError):
            raise obj
        return obj
    finally:
        # If something gone wrong cleanup the process
        try:
            p.kill()
            p.close()
        except AttributeError:  # Process can't be instantiate
            pass
        except ValueError:  # Already terminated
            pass


RESOURCES = Path(__file__).parent / "resources"
LNK_PATH = RESOURCES / "garbage" / "Immersive_Control_Panel.lnk"
