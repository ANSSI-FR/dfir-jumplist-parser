"""Parser module."""

import contextlib
import logging
import os
import re
import struct
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from functools import partial
from io import BytesIO
from typing import Any, cast
from uuid import UUID

from LnkParse3.extra.metadata import SerializedPropertyStorage
from LnkParse3.text_processor import TextProcessor

from .resolver import mac_resolver
from .types import Variant

logger = logging.getLogger(__name__)
UUID_SIZE = 16
VARIANT_TYPES = {
    0: "VT_EMPTY",
    1: "VT_NULL",
    2: "VT_I2",
    3: "VT_I4",
    4: "VT_R4",
    5: "VT_R8",
    6: "VT_CY",
    7: "VT_DATE",
    8: "VT_BSTR",
    9: "VT_DISPATCH",
    10: "VT_ERROR",
    11: "VT_BOOL",
    12: "VT_VARIANT",
    13: "VT_UNKNOWN",
    14: "VT_DECIMAL",
    16: "VT_I1",
    17: "VT_UI1",
    18: "VT_UI2",
    19: "VT_UI4",
    20: "VT_I8",
    21: "VT_UI8",
    22: "VT_INT",
    23: "VT_UINT",
    24: "VT_VOID",
    25: "VT_HRESULT",
    26: "VT_PTR",
    27: "VT_SAFEARRAY",
    28: "VT_CARRAY",
    29: "VT_USERDEFINED",
    30: "VT_LPSTR",
    31: "VT_LPWSTR",
    36: "VT_RECORD",
    37: "VT_INT_PTR",
    38: "VT_UINT_PTR",
    64: "VT_FILETIME",
    65: "VT_BLOB",
    66: "VT_STREAM",
    67: "VT_STORAGE",
    68: "VT_STREAMED_OBJECT",
    69: "VT_STORED_OBJECT",
    70: "VT_BLOB_OBJECT",
    71: "VT_CF",
    72: "VT_CLSID",
    73: "VT_VERSIONED_STREAM",
    0xFFF: "VT_BSTR_BLOB",
    0x1000: "VT_VECTOR",
    0x2000: "VT_ARRAY",
    0x4000: "VT_BYREF",
    0x8000: "VT_RESERVED",
    0xFFFF: "VT_ILLEGAL",
}


def uuid_info(uuid: bytes, prefix: str = "") -> dict[str, Any]:
    """Extract timestamp, mac info and mft sequence from UUID bytes."""
    mac = uuid_to_mac_addr(uuid)
    timestamp = uuid_to_timestamp(uuid)
    return {
        prefix + "timestamp": timestamp.isoformat() if timestamp else None,
        prefix + "mft_seq": uuid_to_mft_seq(uuid),
        prefix + "mac": mac,
        prefix + "vendor": mac_resolver.vendor_from_mac(mac) if mac else None,
    }


def uuid_to_timestamp(uuid: bytes) -> datetime | None:
    """Extract timestamp from UUID bytes (only version 1).

    ref: (rfc4122 and ITU-T Rec. X.667).
    """
    uuid_obj = UUID(bytes_le=uuid)
    if uuid_obj.version == 1:
        # The 60-bit timestamp
        uuid_timestamp = uuid_obj.time
        # For UUID version 1, this is represented by Coordinated Universal Time
        # as a count of 100-nanosecond intervals
        # since 00:00:00.00,15 October 1582
        # (the date of Gregorian reform to the Christian calendar)
        dt = datetime(1582, 10, 15, tzinfo=timezone.utc)
        dt += timedelta(microseconds=uuid_timestamp / 10)
        return dt
    return None


def uuid_to_mft_seq(uuid: bytes) -> int:
    """Extract MFT sequance from UUID bytes."""
    return cast("int", struct.unpack("<H", uuid[8:10])[0])


def uuid_to_mac_addr(uuid: bytes) -> str | None:
    """Extract mac address from UUID bytes (only version 1).

    ref: rfc4122 and ITU-T Rec. X.667
    """
    if UUID(bytes_le=uuid).version == 1:
        return ":".join(f"{part:02x}" for part in uuid[10:16]).upper()
    return None


def uuid_to_str(uuid: bytes) -> str:
    """Extract UUID representation from UUID bytes."""
    return str(UUID(bytes_le=uuid)).upper()


# Support common french accents
RE_NO_PRINTABLE = re.compile(
    r"[^ -~àâäãåçéèêëíìîïñóòôöõúùûüýÿæœÁÀÂÄÃÅÇÉÈÊËÍÌÎÏÑÓÒÔÖÕÚÙÛÜÝŸÆŒ]+",
)


def extract_strings(
    data: bytes | bytearray | memoryview,
    min_size: int = 2,
) -> list[str]:
    """Extract string using encoding."""
    if isinstance(data, memoryview):
        data = data.tobytes()
    strings: list[str] = []
    for padding in range(2):
        strings.extend(
            string
            for string in RE_NO_PRINTABLE.split(
                data[padding:].decode("UTF-16-LE", errors="ignore"),
            )
            if len(string) >= min_size
        )
    strings.extend(
        string
        for string in RE_NO_PRINTABLE.split(
            data[padding:].decode("UTF-8", errors="ignore"),
        )
        if len(string) >= min_size
    )
    return list(dict.fromkeys(strings))


_HITS_NOT_IMPLEMENTED_VARIANT: set[int] = set()


class Buffer(BytesIO):
    """Class used for deserialize bytes."""

    def __init__(self, initial_bytes: bytes) -> None:
        """Instantiate Buffer."""
        super().__init__(initial_bytes)

    def timestamp(self) -> datetime:
        """Read 8 bytes (nsigned long long) and return datetime.datetime."""
        token = self.uint64()
        time = token - (token & 0xF000000000000000)
        if time > 0:
            dt = datetime(1601, 1, 1, tzinfo=timezone.utc)
            dt += timedelta(microseconds=time / 10)
            return dt
        return datetime.min.replace(tzinfo=timezone.utc)

    # Need to patch docstring for sphinx
    def seek(self, offset: int, whence: int = 0, /) -> int:
        """Change stream position.

        Seek to byte offset pos relative to position indicated by whence:

        - 0  Start of stream (the default).  pos should be >= 0;
        - 1  Current position - pos may be negative;
        - 2  End of stream - pos usually negative.

        Returns the new absolute position.
        """
        return super().seek(offset, whence)

    def uuid_str(self) -> str:
        """Read 16 bytes and return an UUID string."""
        return uuid_to_str(self.uuid_raw())

    def uuid_raw(self) -> bytes:
        """Read 16 bytes and return an UUID bytes."""
        value = self.read(16)
        if len(value) != UUID_SIZE:
            msg = "Invalid read of uuid."
            raise TypeError(msg)
        return value

    def mac(self) -> str:
        """Read 6 bytes and return a str representing a mac address."""
        return ":".join(f"{part:02x}" for part in self.read(6))

    def _int(self, pattern: str, size: int) -> int:
        return cast("int", struct.unpack(f"<{pattern}", self.read(size))[0])

    def int8(self) -> int:
        """Read 1 byte and return an signed integer."""
        return self._int("b", 1)

    def uint8(self) -> int:
        """Read 1 byte and return an unsigned integer."""
        return self._int("B", 1)

    def int16(self) -> int:
        """Read 2 bytes and return an signed integer."""
        return self._int("h", 2)

    def uint16(self) -> int:
        """Read 2 bytes and return an unsigned integer."""
        return self._int("H", 2)

    def int32(self) -> int:
        """Read 4 bytes and return an signed integer."""
        return self._int("i", 4)

    def uint32(self) -> int:
        """Read 4 bytes and return an unsigned integer."""
        return self._int("I", 4)

    def int64(self) -> int:
        """Read 8 bytes and return an signed integer."""
        return self._int("q", 8)

    def uint64(self) -> int:
        """Read 8 bytes and return an unsigned integer."""
        return self._int("Q", 8)

    def filetime(self) -> datetime:
        """Read 8 bytes as int64 and convert it into datetime."""
        quad_word = self.uint64()
        us = quad_word // 10
        return datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(
            microseconds=us
        )

    def f64(self) -> float:
        """Read 8 bytes and return a float."""
        return cast("float", struct.unpack("<d", self.read(8))[0])

    def f32(self) -> float:
        """Read 4 bytes and return a float."""
        return cast("float", struct.unpack("<f", self.read(4))[0])

    def b8(self) -> bool:
        """Read 1 byte as boolean."""
        return self.uint8() != 0

    def b16(self) -> bool:
        """Read 2 bytes as boolean."""
        return self.uint16() != 0

    def b32(self) -> bool:
        """Read 4 bytes as boolean."""
        return self.uint32() != 0

    def b64(self) -> bool:
        """Read 8 bytes as boolean."""
        return self.uint64() != 0

    def p32(self) -> int:
        """Read 4 bytes and return 32 bits pointer, alias of uint32."""
        return self.uint32()

    def p64(self) -> int:
        """Read 8 bytes and return 64 bits pointer, alias of uint64."""
        return self.uint64()

    def string(self, size: int | None = None, /) -> str:
        """Read buffer and return a printable string."""
        codecs = ["ascii", "cp1256", "latin-1"]
        data = self.read(size)
        for codec in codecs:
            with contextlib.suppress(Exception):
                return data.decode(codec, errors="strict").rstrip("\x00")
        err_msg = "Invalid text"
        raise ValueError(err_msg)

    def uni(
        self,
        size: int | None = None,
        /,
        *,
        keepend: bool = True,
    ) -> str:
        """Read buffer and return an utf-16 string."""
        if size is not None and not keepend:
            data = self.read(size - 2)
            if self.uint16() != 0:
                logger.warning("Invalid end of string")
            size -= 2
        else:
            data = self.read(size)
        if size is not None and size != len(data):
            logger.warning(
                "Missing %d char from %s",
                size - len(data),
                repr(data),
            )
        return data.decode("UTF-16-LE", errors="ignore")

    def lpstr(self, *, keepend: bool = False) -> str:
        """Read buffer prefixed size and return an utf-16 string."""
        size = self.int32()
        if size <= 0:
            return ""
        return self.uni(size, keepend=keepend)

    def lpwstr(self, *, keepend: bool = False) -> str:
        """Read buffer pow 2 prefixed size and return an utf-16 string."""
        size = self.int32()
        if size <= 0:
            return ""
        size <<= 1
        return self.uni(size, keepend=keepend)

    def read_sized(self) -> bytes:
        """Read buffer and return an bytes array."""
        size = self.uint32()
        return self.read(size)

    def pre_read(self, size: int) -> Callable[[], bytes]:
        """Return a callable for reading bytes."""
        return partial(self.read, size)

    def skip(self, size: int) -> None:
        """Skip bytes without read it."""
        self.seek(size, os.SEEK_CUR)

    def serialized_property_storage(self) -> SerializedPropertyStorage:
        """Get SerializedPropertyStorage."""
        pos = self.tell()
        storage = SerializedPropertyStorage(self.read(), TextProcessor())
        self.seek(pos + storage.storage_size(), os.SEEK_SET)
        return storage

    def variant(self) -> Variant:
        """Parse a variant data."""
        value_type = self.uint16()
        value_name = VARIANT_TYPES.get(value_type, "VT_UNKNOWN")
        self.skip(2)

        def _empty() -> None:
            pass

        # Create warning function
        def _no_implemented() -> str:
            if value_type not in _HITS_NOT_IMPLEMENTED_VARIANT:
                _HITS_NOT_IMPLEMENTED_VARIANT.add(value_type)
                logger.warning(
                    "Not implemented variant type %s (0x%x). "
                    "Future warnings for this type will be silent. "
                    "For more details, see https://learn.microsoft.com/en-us/windows/win32/api/wtypes/ne-wtypes-varenum",
                    value_name,
                    value_type,
                )
            return "NotImplementedError"

        # https://learn.microsoft.com/en-us/windows/win32/api/wtypes/ne-wtypes-varenum
        functions = {
            0: _empty,  # VT_EMPTY
            1: _empty,  # VT_NULL
            2: self.int16,  # VT_I2
            3: self.int32,  # VT_I4
            4: self.f32,  # VT_R4
            5: self.f64,  # VT_R8
            6: _no_implemented,  # VT_CY
            7: _no_implemented,  # VT_DATE
            8: self.lpstr,  # VT_BSTR
            9: self.p64,  # VT_DISPATCH
            10: self.uint32,  # VT_ERROR https://learn.microsoft.com/en-us/office/client-developer/outlook/mapi/scode
            11: self.b64,  # VT_BOOL
            12: self.p64,  # VT_VARIANT
            13: self.p64,  # VT_UNKNOWN
            14: self.pre_read(16),  # VT_DECIMAL
            16: self.int16,  # VT_I1
            17: self.uint8,  # VT_UI1
            18: self.uint16,  # VT_UI2
            19: self.uint16,  # VT_UI4
            20: self.int64,  # VT_I8
            21: self.uint64,  # VT_UI8
            22: self.int32,  # VT_INT
            23: self.uint32,  # VT_UINT
            24: _empty,  # VT_VOID
            25: self.uint32,  # VT_HRESULT https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/705fb797-2175-4a90-b5a3-3918024b10b8
            26: self.p64,  # VT_PTR
            27: _no_implemented,  # VT_SAFEARRAY
            28: _no_implemented,  # VT_CARRAY
            29: _no_implemented,  # VT_USERDEFINED
            30: _no_implemented,  # VT_LPSTR
            31: self.lpwstr,  # VT_LPWSTR
            36: _no_implemented,  # VT_RECORD
            37: _no_implemented,  # VT_INT_PTR
            38: _no_implemented,  # VT_UINT_PTR
            64: self.filetime,  # VT_FILETIME https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-filetime
            65: self.read_sized,  # VT_BLOB
            66: _no_implemented,  # VT_STREAM
            67: _no_implemented,  # VT_STORAGE
            68: _no_implemented,  # VT_STREAMED_OBJECT
            69: _no_implemented,  # VT_STORED_OBJECT
            70: _no_implemented,  # VT_BLOB_OBJECT
            71: _no_implemented,  # VT_CF
            72: self.uuid_str,  # VT_CLSID
            73: _no_implemented,  # VT_VERSIONED_STREAM
            0xFFF: _no_implemented,  # VT_BSTR_BLOB, VT_ILLEGALMASKED, VT_TYPEMASK  # noqa: E501
            0x1000: _no_implemented,  # VT_VECTOR
            0x2000: _no_implemented,  # VT_ARRAY
            0x4000: _no_implemented,  # VT_BYREF
            0x8000: _no_implemented,  # VT_RESERVED
            0xFFFF: _no_implemented,  # VT_ILLEGAL
        }

        func = functions.get(value_type, _no_implemented)
        value = func()  # type: ignore[operator]
        return {
            "value": value,
            "value_type": VARIANT_TYPES.get(value_type, "VT_UNKNOWN"),
        }
