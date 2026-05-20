"""Resolver module."""

import csv
import pathlib
import re
import socket
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from typing_extensions import Protocol

from .types import AppID, FileSystemDict


class PathLike(Protocol):
    """Protocol used for turn an object into a filesystem path."""

    def __fspath__(self) -> str:
        """Get a path from a instance."""


RESOURCES = pathlib.Path(__file__).parent / "resources"
PathStr = str | PathLike | pathlib.PurePath


def to_path(path: Any) -> pathlib.Path:
    """Avoid parsing pathlib.Path."""
    if isinstance(path, pathlib.Path):
        return path
    return pathlib.Path(path or "")


def isoformat(timestamp: float) -> str:
    """Turn timestamp into time represented as ISO."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


class ApplicationResolver:
    """Class used for resolved App ID using filename."""

    _APP_ID_PATH = RESOURCES / "AppID.csv"
    _FILE_RE = re.compile(
        r"(?P<app_id>[0-9a-fA-F]+)\."
        r"(?P<type>automaticDestinations|customDestinations)-ms",
    )

    def __init__(self) -> None:
        """Instantiate ApplicationResolver."""
        self.app_ids: dict[str, AppID] = {}
        with self._APP_ID_PATH.open("r", encoding="utf-8") as file:
            for row in csv.reader(file):
                self.app_ids[row[0].lower()] = {
                    "app_id": row[0].lower(),
                    "name": row[1],
                }

    def app_from_filename(self, filename: str | None) -> AppID:
        """Get an application using an filename."""
        if filename is None:
            return {"app_id": None, "name": None}
        filename = filename.strip()
        match_name = self._FILE_RE.search(filename)
        if match_name is None:
            return {
                "app_id": None,
                "name": None,
            }
        app_id = match_name["app_id"]
        return self.app_from_id(app_id)

    def get_info(self, path: PathStr) -> FileSystemDict:
        """Get information from filesystem."""
        path = to_path(path)
        stat = path.stat() if path.exists() else None
        return {
            "name": path.name,
            "path": str(path),
            "hostname": socket.gethostname(),
            "size": stat.st_size if stat else None,
            "modification_time": isoformat(stat.st_mtime) if stat else None,
            "access_time": isoformat(stat.st_atime) if stat else None,
            "creation_time": isoformat(stat.st_ctime) if stat else None,
            "application": app_resolver.app_from_filename(path.name),
        }

    def app_from_id(self, app_id: str) -> AppID:
        """Get an application using his id."""
        return self.app_ids.get(
            app_id.lower(),
            {
                "app_id": app_id.lower(),
                "name": None,
            },
        )


class UUIDResolver:
    """Class for extract UUID from raw data."""

    _CONTROL_PANEL_PATH = RESOURCES / "UUID.csv"
    RE_UUID = re.compile(
        r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}",
    )
    RE_SHELL_UUID = re.compile(
        r"::{([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})}",
    )

    def __init__(self) -> None:
        """Instantiate ControlPanelResolver."""
        self.uuids: dict[str, str] = {}
        with self._CONTROL_PANEL_PATH.open("r", encoding="utf-8") as file:
            for row in csv.reader(file):
                self.uuids[self.prepare(row[0])] = row[1]

    def prepare(self, uuid: str) -> str:
        """Format GUID."""
        return uuid.replace("{", "").replace("}", "").upper()

    def name_from_uuid(self, uuid: str) -> str | None:
        """Get name from Control Panel UUID."""
        try:
            return self.uuids[self.prepare(uuid)]
        except KeyError:
            return None

    def extract_name(self, data: str) -> str:
        """Extract name from string containing UUID."""

        def _name_or_keep(m: 're.Match["str"]') -> str:
            return self.name_from_uuid(m.group(1)) or m.group(0)

        return self.RE_SHELL_UUID.sub(_name_or_keep, data)

    def extract_info(
        self,
        data: bytes | bytearray | memoryview,
    ) -> dict[str, str]:
        """Extract name from string containing UUID."""
        return {
            uuid: name
            for uuid, name in self.uuids.items()
            if UUID(uuid).bytes_le in data
        }


class MacAddressResolver:
    """Class used for get vendor from MAC Address."""

    _MAC_ADDRESS_PATH = RESOURCES / "MacAddress.csv"

    def __init__(self) -> None:
        """Instantiate MacAddressResolver."""
        self.mac: dict[str, str] = {}
        with self._MAC_ADDRESS_PATH.open("r", encoding="utf-8") as file:
            for row in csv.reader(file):
                self.mac[row[0].upper()] = row[1]

    def vendor_from_mac(
        self,
        mac: bytes | str,
    ) -> str | None:
        """Get name from Control Panel GUID."""
        if isinstance(mac, str):
            mac = mac.replace("-", "").replace(":", "").upper()
        elif isinstance(mac, bytes):
            mac = mac.hex().upper()
        else:
            return None
        if not mac.strip("0"):
            return None
        key = mac[:6]
        try:
            return self.mac[key]
        except KeyError:
            return None


class SpecialFolderResolver:
    """Extract SpecialFolder name using ID."""

    _SPECIAL_FOLDER_PATH = RESOURCES / "SpecialFolder.csv"

    def __init__(self) -> None:
        """Instantiate SpecialFolderResolver."""
        self.folders: dict[str, str] = {}
        with self._SPECIAL_FOLDER_PATH.open("r", encoding="utf-8") as file:
            for row in csv.reader(file):
                self.folders[row[0]] = row[1]

    def name_from_id(self, folder_id: str | int) -> str | None:
        """Get name from SpecialFolder id."""
        try:
            return self.folders[str(folder_id)]
        except KeyError:
            return None


special_folder_resolver = SpecialFolderResolver()
mac_resolver = MacAddressResolver()
uuid_resolver = UUIDResolver()
app_resolver = ApplicationResolver()
