"""Parser for custom destination files.

ref: https://github.com/salehmuhaysin/JumpList_Lnk_Parser/blob/master/JLParser.py
"""

import logging
import struct
from datetime import datetime
from typing import IO

from .buffer import (
    Buffer,
    uuid_to_str,
)
from .exceptions import NotACustomDestinationError
from .info import __version__
from .lnk import inner_parse_lnk
from .log import set_context_path
from .resolver import PathStr, app_resolver
from .types import CustomDestinationDict
from .utils import get_name

logger = logging.getLogger(__name__)


@set_context_path
def parse_custom_destination(
    file_obj: IO[bytes],
    path: PathStr | None = None,
) -> CustomDestinationDict:
    """Parse a file object into a dict."""
    pos = file_obj.tell()
    with Buffer(file_obj.read()) as buf:
        # Get header values
        try:
            version = buf.uint32()
            reserved0 = buf.uint32()
            reserved1 = buf.uint32()
        except struct.error as err:
            file_obj.seek(pos)
            msg = "Not enough bytes to parse"
            raise NotACustomDestinationError(msg) from err
        header_value_type = 0
        text = None
        entry_count = 0
        try:  # Can be missing
            header_value_type = buf.uint32()
            text = buf.lpstr() if header_value_type == 0 else None
            entry_count = buf.int32()
        except struct.error:
            pass
        # Check header values
        if (
            version not in (0, 1, 2)
            or reserved0 not in (0, 1, 2)
            or reserved1 != 0
            or header_value_type not in (0, 1, 2)
        ):
            file_obj.seek(pos)
            msg = (
                "Invalid Custom destination header: "
                f"{version=} {reserved0=} "
                f"{reserved1=} {header_value_type=}"
            )
            raise NotACustomDestinationError(msg)

        # Create custom destination structure
        root: CustomDestinationDict = {
            "type": "custom",
            "status": "success",
            "parser_version": __version__,
            "modification_time": None,
            "filesystem": app_resolver.get_info(path) if path else None,
            "version": version,
            "reserved0": reserved0,
            "reserved1": reserved1,
            "header_value_type": header_value_type,
            "text": text,
            "entry_count": entry_count,
            "lnk": [],
        }
        entry = 0
        try:
            if entry_count > 0:
                for entry in range(entry_count):  # noqa: B007
                    try:
                        guid = buf.uuid_raw()  # Some file doesn't have entries
                    except TypeError:
                        root["status"] = "success"
                        logger.debug(
                            "Missing LNK in custom destination",
                            extra={"path": get_name(file_obj, path)},
                        )
                        break
                    lnk = inner_parse_lnk(buf, garbage=False)
                    lnk["info"] = {"guid": uuid_to_str(guid)}
                    root["lnk"].append(lnk)
                    logger.debug("LNK : %s", repr(lnk))
        except struct.error as err:  # Something gone wrong, save what we can
            root["status"] = "failed"
            logger.warning(
                "Invalid LNK at %d: %s",
                entry,
                repr(root),
                exc_info=err,
            )
        leak = len(buf.read())
        if len(buf.read()) != 0:
            logger.error(
                "Invalid size %s",
                leak,
            )
    max_mtime = max(
        (
            lnk["modification_time"]
            for lnk in root["lnk"]
            if lnk["modification_time"]
        ),
        default=None,
        key=datetime.fromisoformat,
    )
    root["modification_time"] = max_mtime
    return root
