"""Test for command line interface."""

import contextlib
import io
import os
import re
import subprocess
import sys

import pytest

from jumplist_parser import entrypoint
from tests.utils import LNK_PATH


def test_cli_version() -> None:
    """Test if the command line interface is installed correctly."""
    name = "jumplist-parser"
    env = os.environ.get("VIRTUAL_ENV", "")
    if env:
        if os.name == "nt":
            exe = f"{env}\\\\Scripts\\\\{name}.cmd"
            if not os.path.exists(exe):  # noqa: PTH110
                exe = f"{env}\\\\Scripts\\\\{name}.exe"
        else:
            exe = f"{env}/bin/{name}"
    else:
        exe = name
    out = subprocess.check_output((exe, "--version"), text=True, shell=False)
    assert "version" in out
    out = subprocess.check_output(
        (
            sys.executable,
            "-m",
            "jumplist_parser",
            "--version",
        ),
        text=True,
        shell=False,
    )
    assert "version" in out
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout), pytest.raises(SystemExit):
        entrypoint(("--version",))
    assert "version" in stdout.getvalue()


def test_import() -> None:
    """Test if module entrypoint has correct imports."""
    import jumplist_parser.__main__  # noqa: PLC0415, F401


def test_jumplist_parser_cli() -> None:
    """Test command jumplist_parser."""
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        entrypoint((str(LNK_PATH),))
    assert re.search(r',\s*"status":\s*"success",', stdout.getvalue())
