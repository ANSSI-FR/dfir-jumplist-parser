"""Parser for automatic destinations files.

ref: https://github.com/salehmuhaysin/JumpList_Lnk_Parser/blob/master/JLParser.py
ref: https://github.com/EricZimmerman/JumpList/blob/master/JumpList/Automatic/AutomaticDestination.cs
ref: https://github.com/EricZimmerman/ExtensionBlocks/blob/master/ExtensionBlocks/PropertySheet.cs
"""

import base64
import hashlib
import logging
import struct
from datetime import datetime
from typing import IO, Any, Literal, cast

import olefile

from .buffer import (
    Buffer,
    uuid_info,
    uuid_to_str,
)
from .exceptions import NotAnAutomaticDestinationError
from .info import __version__
from .lnk import inner_parse_lnk
from .log import set_context_path
from .resolver import PathStr, app_resolver, uuid_resolver
from .types import (
    LNK,
    AutomaticDestEntry,
    AutomaticDestinationDict,
    ErrorLNK,
    PropertySheetDict,
)

logger = logging.getLogger(__name__)

DEST_LIST_HEADER = 76
UNPINNED_VALUE = 0xFFFFFFFF
DEST_LIST_PROPERTY_STORE = "DestListPropertyStore"
DEST_LIST = "DestList"
VERSIONS = {
    1: "Win7/8",
    3: "Win10 build 1511",
    4: "Win10 build 1607",
    5: "Win11",
}


@set_context_path
def parse_automatic_destination(  # noqa: PLR0912
    file_obj: IO[bytes],
    path: PathStr | None = None,
) -> AutomaticDestinationDict:
    """Parse a file object into a dict."""
    pos = file_obj.tell()
    is_ole = olefile.isOleFile(file_obj)
    file_obj.seek(pos)
    if not is_ole:
        raise NotAnAutomaticDestinationError(file_obj)
    root: AutomaticDestinationDict = {
        "type": "automatic",
        "status": "success",
        "parser_version": __version__,
        "modification_time": None,
        "filesystem": app_resolver.get_info(path) if path else None,
        "dest_list_property_store": None,
        "dest_list": None,
        "lnk": [],
    }

    # Open OLEfile
    with olefile.OleFileIO(file_obj) as ole:
        for i, ole_dir in enumerate(ole.listdir()):
            ole_name = ole_dir[0]
            logger.debug("OLE : %s", repr(ole_dir))
            stream = ole.openstream(ole_name)
            data = stream.read()
            logger.debug("Buffer OLe Item : %s", repr(data))
            if not data:
                logger.debug("Empty file")
            else:
                with Buffer(data) as buf:
                    stream_header = buf.uint32()
                    buf.seek(0)
                    if ole_name == DEST_LIST_PROPERTY_STORE:
                        # This item is an DestListPropertyStore
                        if stream_header != 0:
                            props = _parser_dest_list_property_header(buf)
                            root["dest_list_property_store"] = props
                    elif ole_name == DEST_LIST:
                        # This item is an DestList
                        logger.debug(
                            "Parsing Dest List",
                            extra={"stream_header": stream_header},
                        )
                        try:
                            root["dest_list"] = _parser_dest_list(buf)  # type: ignore[typeddict-item]
                        except struct.error as err:
                            root["status"] = "failed"
                            logger.warning(
                                "Cannot parse Dest List at %d %r",
                                i,
                                ole_dir,
                                exc_info=err,
                            )
                    else:
                        # This item is a LNK
                        try:
                            lnk: LNK | ErrorLNK = inner_parse_lnk(
                                buf,
                                garbage=True,
                            )
                        except struct.error as err:
                            data = buf.read()
                            lnk = {
                                "type": "error",
                                "status": "failed",
                                "modification_time": None,
                                "size": len(data),
                                "data_base64": base64.b64encode(data).decode(),
                                "data_sha256": hashlib.sha256(
                                    data
                                ).hexdigest(),
                            }
                            logger.warning(
                                "Invalid LNK at %d %r",
                                i,
                                ole_dir,
                                exc_info=err,
                            )
                        lnk["info"] = {"entry_id_number": ole_name}
                        root["lnk"].append(lnk)
    _merge_dest_list(root)
    for entry in root["lnk"]:
        if "info" in entry:
            info = entry["info"]
            if "modification_time" in info:
                entry["modification_time"] = info["modification_time"]  # type: ignore[typeddict-item]
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


def _merge_dest_list(root: AutomaticDestinationDict) -> None:
    """Merge DestList with LNKs."""
    if root["dest_list"]:
        merge = root["dest_list"].pop("entries", [])  # type: ignore[typeddict-item]
        orphan_entries = []
        for dest in merge:
            entry_id_number = dest["entry_id_number"]
            for lnk in root["lnk"]:
                if lnk["type"] != "lnk":
                    continue
                lnk_id_number = lnk["info"]["entry_id_number"]  # type: ignore[typeddict-item]
                if lnk_id_number == entry_id_number:
                    if "checksum" in lnk["info"]:  # check if already exist
                        root["status"] = "failed"
                        logger.warning(
                            "Duplicated destlist : %s",
                            entry_id_number,
                        )
                        orphan_entries.append(dest)
                        break
                    lnk["info"].update(dest)
                    break
            else:
                root["status"] = "failed"
                available = ", ".join(
                    repr(lnk["info"]["entry_id_number"])  # type: ignore[typeddict-item]
                    for lnk in root["lnk"]
                )
                logger.warning(
                    "Invalid dest, %s %s",
                    entry_id_number,
                    available,
                )
                orphan_entries.append(dest)
        root["dest_list"]["orphan_entries"] = orphan_entries


def _parser_dest_list_property_header(buf: Buffer) -> PropertySheetDict:
    """Parse DestListPropertyStore block in AutomaticDestination."""
    header = buf.uint32()
    storage = buf.serialized_property_storage()
    return {"header": header, **storage.as_dict()}  # type: ignore[typeddict-item]


def _parser_dest_list(buf: Buffer) -> dict[str, Any]:
    """Parse DestList block in AutomaticDestination."""
    version = buf.uint32()
    header: dict[str, Any] = {
        "file_version": version,
        "total_current_entries": buf.uint32(),
        "total_pinned_entries": buf.uint32(),
        "reserved0": buf.f32(),
        "last_issued_id_num": buf.uint32(),
        "reserved1": buf.uint32(),
        "number_of_actions": buf.uint32(),
        "reserved2": buf.uint32(),
        "os": VERSIONS.get(version, "Unknown"),
    }
    entries = []
    logger.debug("Buffer : %s", repr(header))
    for _ in range(header["total_current_entries"]):
        checksum = f"{buf.uint64():016x}"
        droid_volume_identifier = buf.uuid_raw()
        droid_file_identifier = buf.uuid_raw()
        birth_droid_volume_identifier = buf.uuid_raw()
        birth_droid_file_identifier = buf.uuid_raw()
        hostname = buf.string(16)
        if version in (0, 1):
            entry_id = buf.uint32()
            buf.skip(4)
            access_counter = buf.f32()  # Verify this
            modification_time = buf.timestamp().isoformat()
            pin_value = buf.uint32()
            data_len = buf.uint16() << 1
            data = buf.uni(data_len)
        else:
            if version not in (2, 3, 4, 5):
                logger.warning("New DestList version detected: %r", version)
            entry_id = buf.uint32()
            buf.skip(8)
            modification_time = buf.timestamp().isoformat()
            pin_value = buf.uint32()
            buf.skip(4)
            access_counter = float(buf.uint32())
            buf.skip(8)
            data_len = buf.uint16() << 1
            data = buf.uni(data_len)
            buf.skip(4)
        if pin_value == UNPINNED_VALUE:
            pin_status: Literal["Unpinned", "Pinned", "Unknown"] = "Unpinned"
        elif pin_value >= 0:
            pin_status = "Pinned"
        else:
            pin_status = "Unknown"

        entry = cast(
            "AutomaticDestEntry",
            {
                "checksum": checksum,
                "droid_volume_identifier": uuid_to_str(
                    droid_volume_identifier,
                ),
                "droid_file_identifier": uuid_to_str(droid_file_identifier),
                **uuid_info(droid_file_identifier, "droid_file_"),
                "birth_droid_volume_identifier": uuid_to_str(
                    birth_droid_volume_identifier,
                ),
                "birth_droid_file_identifier": uuid_to_str(
                    birth_droid_file_identifier,
                ),
                **uuid_info(birth_droid_file_identifier, "birth_droid_file_"),
                "hostname": hostname,
                "modification_time": modification_time,
                "pin_value": pin_value,
                "pin_status": pin_status,
                "entry_id_number": f"{entry_id:x}",
                "access_counter": access_counter,
                "data": data,
                "name": uuid_resolver.extract_name(data),
            },
        )
        logger.debug("Dest List information: %s", repr(entry))
        entries.append(entry)
    header["entries"] = entries
    return header
