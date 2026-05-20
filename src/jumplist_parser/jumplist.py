"""Parser for jumplist.

ref: https://github.com/libyal/dtformats/blob/main/documentation/Jump%20lists%20format.asciidoc
"""

import logging
from contextlib import suppress
from typing import IO

from .automatic import parse_automatic_destination
from .custom import parse_custom_destination
from .exceptions import (
    NotACustomDestinationError,
    NotALNKError,
    NotAnAutomaticDestinationError,
    UnparsableJumpListError,
)
from .info import __version__
from .lnk import parse_lnk
from .log import set_context_path
from .resolver import PathStr, app_resolver
from .types import ErrorDict, JumpEntry
from .utils import is_ext_attrs, is_msdelta_patch_file

logger = logging.getLogger(__name__)


@set_context_path
def parse_jumplist(
    file_obj: IO[bytes],
    path: PathStr | None = None,
) -> JumpEntry:
    """Parse abstract jumplist."""
    pos = file_obj.tell()

    try:
        # Check automatic destination
        with suppress(NotAnAutomaticDestinationError):
            return parse_automatic_destination(file_obj, path)

        # Check Custom destination
        with suppress(NotACustomDestinationError):
            return parse_custom_destination(file_obj, path)

        # Check LNK File
        with suppress(NotALNKError):
            return parse_lnk(file_obj, path)

        # Debug information
        if logger.isEnabledFor(logging.DEBUG):
            if is_ext_attrs(file_obj):
                logger.debug(
                    "File seems to be an extended file attribute: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-smb/65e0c225-5925-44b0-8104-6b91339c709f"
                )
            else:
                file_obj.seek(pos)
            if is_msdelta_patch_file(file_obj):
                logger.debug(
                    "File seems to be an MSDelta Patch file: https://learn.microsoft.com/en-us/windows/win32/devnotes/msdelta"
                )
            file_obj.seek(pos)
            buffer = file_obj.read()
            logger.debug("Buffer %s", buffer.hex(":"))

        msg = "Unknown JumpList file."
        raise UnparsableJumpListError(msg)  # noqa: TRY301
    except Exception as err:  # noqa: BLE001
        # Failed to parse JumpList
        message = f"{type(err).__name__}: {err}"
        if logger.isEnabledFor(logging.DEBUG):
            logger.warning(message, exc_info=err)
        else:
            logger.warning(message)

        # Error json
        error: ErrorDict = {
            "type": "error",
            "status": "failed",
            "parser_version": __version__,
            "message": message,
            "filesystem": app_resolver.get_info(path) if path else None,
            "lnk": [],
        }
        return error
