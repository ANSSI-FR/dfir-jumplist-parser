"""Utilities."""

import re
from typing import IO, Any


def update_after(
    src: Any,
    key: Any,
    obj: Any,
) -> None:
    """Insert dict into another after a given key.

    >>> a = {0: 1, 1: 3}
    >>> update_after(a, 0, {2: 3})
    >>> print(a)
        {0: 1, 2: 3, 1: 3}
    """
    items = tuple(src.items())
    src.clear()
    updated = False
    for k, v in items:
        src[k] = v
        if key == k:
            src.update(obj)
            updated = True
    if not updated:
        src.update(obj)


def get_name(obj: Any, default: Any) -> str:
    """Get name from object."""
    try:
        name = obj.name
        if name:
            return str(name)
    except AttributeError:
        pass
    return str(default)


EXT_ATTRS_HEADER_SIZE = 8
EXT_ATTRS_RE = re.compile(rb"[\s\S]\x00\x00\x00\x00[\s\S][\s\S]\x00")


def is_ext_attrs(file_obj: IO[bytes]) -> bool:
    """Check if bytes are an extended attributes."""
    header = file_obj.read(8)
    return (
        len(header) >= EXT_ATTRS_HEADER_SIZE
        and EXT_ATTRS_RE.match(header) is not None
    )


def is_msdelta_patch_file(file_obj: IO[bytes]) -> bool:
    """Check if bytes are an msdelta patch file.

    ref: https://learn.microsoft.com/en-us/windows/win32/devnotes/msdelta
    ref: https://stackoverflow.com/questions/74207060/cannot-apply-patch-file-using-msdelta
    """
    header = file_obj.read(8)
    return header[4:8] == b"PA30"
