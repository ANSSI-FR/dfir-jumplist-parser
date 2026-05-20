"""Parser for LNK file.

ref: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-shllink/16cb4ca1-9339-4d0c-a68d-bf1d6cc0f943
ref: https://github.com/libyal/liblnk/wiki
ref: https://github.com/Matmaus/LnkParse3/
"""

import logging
import os
import struct
from base64 import b64encode
from struct import unpack
from typing import IO
from uuid import UUID

import LnkParse3
from LnkParse3.extra.terminal import Terminal

from .buffer import uuid_info
from .exceptions import NotALNKError
from .info import __version__
from .log import set_context_path
from .resolver import (
    PathStr,
    app_resolver,
    special_folder_resolver,
)
from .types import LNK, LNKDict
from .utils import update_after

logger = logging.getLogger(__name__)
HEADER_SIZE_LNK = 0x0000004C


@set_context_path
def parse_lnk(
    file_obj: IO[bytes],
    path: PathStr | None = None,
) -> LNKDict:
    """Parse LNK file and replace cursor at end."""
    pos = file_obj.tell()
    header = file_obj.read(4)
    file_obj.seek(pos)
    if header != b"L\x00\x00\x00":
        msg = f"Invalid LNK header: {header!r}"
        raise NotALNKError(msg)
    lnk = inner_parse_lnk(file_obj, garbage=True)
    return {
        "type": "lnk",
        "status": lnk["status"],
        "parser_version": __version__,
        "modification_time": lnk["header"]["modification_time"],
        "filesystem": app_resolver.get_info(path) if path else None,
        "lnk": [lnk],
    }


def inner_parse_lnk(  # noqa: C901, PLR0912, PLR0915
    file_obj: IO[bytes],
    *,
    garbage: bool = False,
) -> LNK:
    """Parse embed LNK without wrapping."""
    # Save current position in file and raise for avoid unnecessary warning
    header = file_obj.read(4)
    pos = file_obj.seek(-4, os.SEEK_CUR)
    size = unpack("<I", header)[0]

    if size != HEADER_SIZE_LNK:
        message = f"Wrong header, expected {HEADER_SIZE_LNK} got {size}"
        raise struct.error(message)

    # Parse lnk
    file = LnkParse3.lnk_file(file_obj)
    data: LNK = {  # type: ignore[typeddict-item]
        "type": "lnk",
        "status": "success",
        **file.get_json(get_all=True),
    }

    # Compute lnk size
    # NOTE: https://github.com/Matmaus/LnkParse3/pull/51
    if "data" in data:
        data["data"]["size"] = file.string_data.size()
    header_size = data["header"]["header_size"]
    try:
        target_size = data["target"]["size"] + 2
    except KeyError:
        target_size = 0
    parts = (
        header_size,
        target_size,
        data.get("link_info", {}).get("link_info_size", 0),
        data["data"]["size"],
        sum(extra["size"] for extra in data.get("extra", {}).values()),  # type: ignore[index]
        4,
    )
    data["size"] = sum(parts)

    # Resolve special folder for extra SPECIAL_FOLDER_LOCATION_BLOCK
    try:
        folder = data["extra"]["SPECIAL_FOLDER_LOCATION_BLOCK"]
        folder_id = folder["special_folder_id"]
        folder_name = special_folder_resolver.name_from_id(folder_id)
        folder["special_folder_name"] = folder_name
    except KeyError:
        pass

    # Add info on file_identifier in DISTRIBUTED_LINK_TRACKER_BLOCK
    for prefix in ("droid_file_", "birth_droid_file_"):
        key = prefix + "identifier"
        try:
            tracker = data["extra"]["DISTRIBUTED_LINK_TRACKER_BLOCK"]
            identifier = UUID(tracker[key]).bytes_le  # type: ignore[literal-required]
            update_after(tracker, key, uuid_info(identifier, prefix))
        except KeyError:
            pass

    # Rename attributes with bad names
    mtime = data["header"].pop("modified_time")  # type: ignore[typeddict-item]
    atime = data["header"].pop("accessed_time")  # type: ignore[typeddict-item]
    ctime = data["header"].pop("creation_time")  # type: ignore[misc]
    update_after(
        data["header"],
        "r_file_flags",
        {
            "modification_time": mtime.isoformat() if mtime else None,
            "access_time": atime.isoformat() if atime else None,
            "creation_time": ctime.isoformat() if ctime else None,  # type: ignore[attr-defined]
        },
    )

    # Replace the file cursor at the LNK end or collect garbage
    for extra in file.extras:
        if isinstance(extra, Terminal):
            size = extra.size()
            file_obj.seek(pos + data["size"] - size)
            if garbage:
                raw = b64encode(extra._raw).decode("utf-8")  # noqa: SLF001
                if "extra" not in data:
                    data["extra"] = {}
                data["extra"]["TERMINAL_BLOCK"]["appended_data_base64"] = raw
            else:
                file_obj.seek(pos + data["size"] - size)
                data["size"] -= size
                del data["extra"]["TERMINAL_BLOCK"]
            break

    # Update modification_time from header
    update_after(
        data,
        "status",
        {"modification_time": data["header"]["modification_time"]},
    )

    # Convert datetime to str
    if "target" in data:
        for target in data["target"]["items"]:
            if target.get("modification_time"):
                target["modification_time"] = target[  # type: ignore[typeddict-unknown-key,union-attr]
                    "modification_time"  # type: ignore[typeddict-item]
                ].isoformat()

    return data
