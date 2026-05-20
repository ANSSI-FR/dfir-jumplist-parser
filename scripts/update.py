"""Updated files in src/jumplist_parser/resources."""

import csv
import logging
import pathlib
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from inspect import signature
from io import BytesIO
from time import sleep

import orjson

from jumplist_parser.jumplist import parse_jumplist

HERE = pathlib.Path(__file__).parent.resolve()
ROOT = HERE.parent
SRC = ROOT / "src" / "jumplist_parser"
RESOURCES = SRC / "resources"
DATA = ROOT / "tests" / "resources" / "data.tar.xz"
SAMPLES = ROOT / "docs" / "samples"


def get(url: str) -> bytes:
    """Send GET request and return bytes."""
    if not url.startswith(("http://", "https://")):
        err_msg = "URL must start with 'http:' or 'https:'"
        raise ValueError(err_msg)
    with urllib.request.urlopen(url) as response:  # NoQA: S310
        return response.read()  # type: ignore[no-any-return]


RE_ESPACE = re.compile(r"\s+")


def sanitize_app_name(text: str) -> str:
    """Sanitize output to printable strings."""
    for src, dst in (
        ("\uff09", ") "),
        ("\uff08", " ("),
        ("\uff02", ", "),
        ("\uff0c", ", "),
        ("\xa0", " "),
        ("-", "-"),
        ("—", "-"),
        ("\u2018", "'"),
        ("\u2002", " "),
        ("\u200b", " "),
        ("`", "'"),
        ("  ", " "),
        ("  ", " "),
        ("  ", " "),
        ("  ", " "),
        ("  ", " "),
        (" .", "."),
    ):
        text = text.replace(src, dst)
    return text.strip()


def sanitize_app_id(text: str) -> str:
    """Sanitize output to printable strings."""
    return f"{text.strip().upper():>016}"


TZWORKS_APP_IDS_URl = (
    "https://tzworks.com/prototypes/jmp/jmp64.v.0.64.lin.tar.gz"
)


def _fetch_tzwork_app_ids() -> dict[str, str]:
    """Fetch AppIDs from tzworks.com.

    Ref: https://tzworks.com/download_links.php -> jmp64.tar.gz -> appids.txt
    """
    tar_content = get(TZWORKS_APP_IDS_URl)
    raw_tar_file = BytesIO(tar_content)
    app_ids = {}
    with tarfile.open(fileobj=raw_tar_file) as archive:
        for member in archive.getmembers():
            if "appids" not in member.name or not member.isreg():
                continue
            file = archive.extractfile(member.name)
            if file:
                try:
                    content = file.read()
                finally:
                    file.close()
            for line in content.splitlines():
                if line.strip().startswith(b"//"):
                    continue
                parts = line.decode("utf-8").split("|", 1)
                if len(parts) != 2:  # noqa: PLR2004
                    continue
                app_id, app_name = parts
                app_name = sanitize_app_name(app_name)
                app_id = sanitize_app_id(app_id)
                if not app_id or not app_name:
                    continue
                app_ids[app_id] = app_name
    return app_ids


RE_FORENSICS_WIKI = re.compile(
    rb"<tr>[\s\r\n]*"
    rb"<td>[\s\r\n]*(?P<appid>[a-zA-Z0-9]+?)[\s\r\n]*</td>[\s\r\n]*"
    rb"<td>[\s\r\n]*(?P<appname>.+?)[\s\r\n]*</td>",
    flags=re.MULTILINE,
)


def _fetch_forensics_wiki_app_ids() -> dict[str, str]:
    """Fetch AppIDs from forensics.wiki.

    ref: https://forensics.wiki/list_of_jump_list_ids/
    """
    url = "https://forensics.wiki/list_of_jump_list_ids/"
    app_ids = {}
    content = get(url)
    for match in RE_FORENSICS_WIKI.finditer(content):
        app_id = sanitize_app_id(match["appid"].decode("utf-8"))
        app_name = sanitize_app_name(match["appname"].decode("utf-8"))
        app_ids[app_id] = app_name
    return app_ids


def _fetch_eric_zimmerman_app_ids() -> dict[str, str]:
    """Fetch AppIDs from github.com/EricZimmerman/JumpList.

    ref: https://github.com/EricZimmerman/JumpList/blob/master/JumpList/Resources/AppIDs.txt
    """
    app_id = (
        get(
            "https://raw.githubusercontent.com/EricZimmerman/JumpList/master/JumpList/Resources/AppIDs.txt",
        )
        .decode("utf-8")
        .lstrip("\ufeff")
    )
    reader = csv.reader(app_id.splitlines(), delimiter="|")
    return {
        sanitize_app_id(row[0]): sanitize_app_name(row[1].strip())
        for row in reader
    }


def update_app_ids() -> None:
    """Update AppID.csv from many sources.

    ref: https://github.com/EricZimmerman/JumpList/blob/master/JumpList/Resources/AppIDs.txt
    ref: https://forensics.wiki/list_of_jump_list_ids/
    ref: https://tzworks.com/download_links.php
    """
    print(
        "[+] Update AppID.csv from https://github.com/EricZimmerman/JumpList/blob/master/JumpList/Resources/AppIDs.txt"
    )
    app_ids = _fetch_tzwork_app_ids()
    print(
        "[+] Update AppID.csv from https://forensics.wiki/list_of_jump_list_ids/"
    )
    app_ids |= _fetch_forensics_wiki_app_ids()
    print("[+] Update AppID.csv from https://tzworks.com/download_links.php")
    app_ids |= _fetch_eric_zimmerman_app_ids()

    path = RESOURCES / "AppID.csv"
    with path.open("w", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(sorted(app_ids.items()))


def update_mac_address() -> None:
    """Update MacAddress.csv.

    ref: https://regauth.standards.ieee.org/standards-ra-web/pub/view.html#registries
    """
    max_retry = 3
    for _ in range(max_retry):
        try:
            mac = get("https://standards-oui.ieee.org/oui/oui.csv").decode(
                "utf-8"
            )
            print(
                "[+] Update MacAddress.csv from https://standards-oui.ieee.org/oui/oui.csv"
            )
        except urllib.error.HTTPError:  # noqa: PERF203
            print(
                "[!] Failed to fetch https://standards-oui.ieee.org/oui/oui.csv, retry in 30 sec",  # noqa: E501
                file=sys.stderr,
            )
            sleep(30)
        else:
            break
    else:
        print(
            "[X] Unable to fetch https://standards-oui.ieee.org/oui/oui.csv, please retry later",  # noqa: E501
            file=sys.stderr,
        )
        return
    mac = mac.split("\n", 1)[-1]
    path = RESOURCES / "MacAddress.csv"
    reader = csv.reader(mac.splitlines())
    with path.open("w", encoding="utf-8") as file:
        writer = csv.writer(file)
        lines = [
            (row[1].strip().upper(), sanitize_app_name(row[2].strip()))
            for row in reader
        ]
        lines.sort()
        writer.writerows(lines)


RE_CONTROL_PANEL = re.compile(
    r"""
    <li>
        [\s\n\r]*(?:<p>)?[\s\n\r]*
            <strong>Canonical\ name</strong>
            [\s\n\r]*:[\s\n\r]*
            (?P<name>[^<]+)
        [\s\n\r]*(?:</p>)?[\s\n\r]*
    </li>
    [\s\n\r]*
    <li>
        [\s\n\r]*(?:<p>)?[\s\n\r]*
            <strong>GUID</strong>
            [\s\n\r]*:[\s\n\r]*
            {(?P<guid>[^\}]+)}
        [\s\n\r]*(?:</p>)?[\s\n\r]*
    </li>
    """,
    re.VERBOSE,
)
RE_CONTROL_PANEL_DECRECIATED = re.compile(
    r"""
    <td>(?P<name>[^<]+)</td>
    [\s\n\r.]*
    <td>[^<]+</td>
    [\s\n\r]*
    <td>{(?P<guid>[^\}]+)}</td>
    """,
    re.VERBOSE,
)

RE_UUID_NAME = re.compile(r"^(?:CLSID|IID) (.+)")


def update_uuid() -> None:
    """Update UUID.csv.

    ref: https://learn.microsoft.com/en-us/windows/win32/shell/controlpanel-canonical-names
    ref: https://gist.github.com/olafhartong/980e9cd51925ff06a5a3fdfb24fb96c2
    """
    print(
        "[+] Update UUID.csv from https://learn.microsoft.com/en-us/windows/win32/shell/controlpanel-canonical-names"
    )
    cp = get(
        "https://learn.microsoft.com/en-us/windows/win32/shell/controlpanel-canonical-names",
    ).decode("utf-8")
    path = RESOURCES / "UUID.csv"

    def pretty_name(name: str) -> str:
        return re.sub(
            r"([a-z])([A-Z])",
            r"\1 \2",
            name.split("Microsoft.", 1)[-1],
        )

    uuids = {}
    for m in RE_CONTROL_PANEL.finditer(cp):
        uuids[m.group("guid").upper()] = pretty_name(m.group("name"))
    for m in RE_CONTROL_PANEL_DECRECIATED.finditer(cp):
        uuids[m.group("guid").upper()] = pretty_name(m.group("name"))

    print(
        "[+] Update UUID.csv from https://gist.githubusercontent.com/olafhartong/980e9cd51925ff06a5a3fdfb24fb96c2/raw/16253a7ac2f7ae1ecf338790236297d6b28efa9f/Windows-CLSID.csv"
    )
    cp2 = get(
        "https://gist.githubusercontent.com/olafhartong/980e9cd51925ff06a5a3fdfb24fb96c2/raw/16253a7ac2f7ae1ecf338790236297d6b28efa9f/Windows-CLSID.csv",
    ).decode("utf-8")
    lines = cp2.splitlines()[1:]
    for line in lines:
        raw_uuid, name = line.split(",", 1)
        uuid = raw_uuid.replace("{", "").replace("}", "").upper()
        if uuid not in uuids:
            ma = RE_UUID_NAME.fullmatch(name)
            if ma:
                uuids[uuid] = ma.group(1)

    with path.open("w", encoding="utf-8") as file:
        writer = csv.writer(file)
        for uuid, name in uuids.items():
            writer.writerow((uuid, name))


RE_SPECIAL_FOLDER = re.compile(
    r"""
    <td\s+id="[a-z-]+">
    [\s\n\r]*
    (?P<name>.+)
    [\s\n\r]*
    </td>
    [\s\n\r]*
    <td>
    [\s\n\r]*
    (?P<id>[0-9]+)
    [\s\n\r]*
    </td>
    """,
    re.VERBOSE,
)


def update_special_folder() -> None:
    """Update SpecialFolder.csv.

    ref: https://learn.microsoft.com/fr-fr/dotnet/api/system.environment.specialfolder
    """
    print(
        "[+] Update SpecialFolder.csv from https://learn.microsoft.com/fr-fr/dotnet/api/system.environment.specialfolder"
    )
    sf = get(
        "https://learn.microsoft.com/fr-fr/dotnet/api/system.environment.specialfolder",
    ).decode("utf-8")
    folders = [
        (int(m.group("id")), m.group("name"))
        for m in RE_SPECIAL_FOLDER.finditer(sf)
    ]
    folders.sort()
    path = RESOURCES / "SpecialFolder.csv"
    with path.open("w", encoding="utf-8") as file:
        writer = csv.writer(file)
        for folder in folders:
            writer.writerow(folder)


def update_samples() -> None:
    """Update samples in documentations."""
    print("[+] Update docs/samples/*.json from data.tar.xz")
    SAMPLES.mkdir(parents=True, exist_ok=True)
    if DATA.exists():
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir)
            try:
                with tarfile.open(DATA) as tar:
                    for original_path, extracted_name, destination_name in (
                        (
                            "W11-22H2U/ORC_WorkStation_W11-22H2U_General.7z/Artefacts.7z/recentFile/48F2EAC0F2EAB0FC_2000000017FCE_1000000018041_4_5a2098e080cf7ac4.automaticDestinations-ms_{00000000-0000-0000-0000-000000000000}.data",
                            "5a2098e080cf7ac4.automaticDestinations-ms",
                            "dest_list_automaticDestinations-ms.json",
                        ),
                        (
                            "W2012R2SP1/ORC_Server_W2012R2SP1_General.7z/Artefacts.7z/recentFile/74B0257BB02544C8_100000001A84D_100000001A84E_4_f01b4d95cf55d32a.automaticDestinations-ms_{00000000-0000-0000-0000-000000000000}.data",
                            "f01b4d95cf55d32a.automaticDestinations-ms",
                            "automaticDestinations-ms.json",
                        ),
                        (
                            "APPS2019-SP/ORC_Server_APPS2019-SP.apps2019.lab_General.7z/Artefacts.7z/recentFile/280420FE0420D09C_2000000016935_3000000015A88_4_28c8b86deab549a1.customDestinations-ms_{00000000-0000-0000-0000-000000000000}.data",
                            "28c8b86deab549a1.customDestinations-ms",
                            "customDestinations-ms.json",
                        ),
                        (
                            "W11PRO-22000-51/ORC_WorkStation_W11PRO-22000-51_General.7z/Artefacts.7z/lnk/84B6B902B6B8F5B0_10000000005DC_100000000F896_4_Windows_PowerShell.lnk_{00000000-0000-0000-0000-000000000000}.data",
                            "Windows PowerShell.lnk",
                            "lnk.json",
                        ),
                        (
                            "W11PRO-22000-51/ORC_WorkStation_W11PRO-22000-51_General.7z/Residents.7z/fichiers_residents/84B6B902B6B8F5B0_10000000011FC_100000000F836_4_02_-_Windows_Terminal.lnk_{00000000-0000-0000-0000-000000000000}.data",
                            "02 - Windows Terminal.lnk",
                            "unknown.json",
                        ),
                    ):
                        extracted_path = tmp_path / extracted_name
                        destination_path = SAMPLES / destination_name
                        extract_sig = signature(tarfile.TarFile.extract)
                        if "filter" in extract_sig.parameters:
                            tar.extract(original_path, tmp_path, filter="data")
                        else:
                            tar.extract(original_path, tmp_path)
                        tmp_extracted_path = tmp_path / original_path
                        shutil.copy2(str(tmp_extracted_path), extracted_path)
                        tmp_extracted_path.unlink()
                        with extracted_path.open("rb") as file:
                            res = parse_jumplist(file, extracted_path)
                            fs = res["filesystem"]
                            if fs:
                                fs["path"] = fs["path"].replace(
                                    tmp_path.name,
                                    "abcdefg",
                                )
                                fs["hostname"] = "jumplist_parser"
                                fs["creation_time"] = (
                                    "2023-07-25T14:04:47+00:00"
                                )
                                fs["access_time"] = "2023-07-25T14:06:47+00:00"
                            json = orjson.dumps(
                                res,
                                option=orjson.OPT_INDENT_2,
                            )
                            destination_path.write_bytes(json + b"\n")
            finally:
                shutil.rmtree(tmp_path)
    else:
        errmsg = f"Missing {DATA}"
        raise FileNotFoundError(errmsg)


def update_all() -> None:
    """Update all resources."""
    logging.basicConfig(level=logging.ERROR)
    update_samples()
    update_app_ids()
    update_uuid()
    update_mac_address()
    update_special_folder()

    print("[+] Update UpdateInfo.txt")
    info = RESOURCES / "UpdateInfo.txt"
    info.write_text(f"Last update at {datetime.now(tz=timezone.utc)}\n")


if __name__ == "__main__":
    update_all()
