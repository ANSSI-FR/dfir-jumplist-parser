"""Test with ptf2ref."""

import logging
import secrets
from base64 import b64encode
from io import BytesIO

from jumplist_parser import parse_lnk
from tests.utils import LNK_PATH

logger = logging.getLogger(__name__)
SIZE = 32


def test_garbage() -> None:
    """Check garbage on lnk."""
    token = secrets.token_bytes(SIZE)
    raw = LNK_PATH.read_bytes()
    b64token = b64encode(raw[-4:] + token).decode("utf-8")
    file_obj = BytesIO(raw + token)
    file_obj.name = str(file_obj)
    lnk = parse_lnk(file_obj, path=LNK_PATH)
    terminal = lnk["lnk"][0]["extra"]["TERMINAL_BLOCK"]  # type: ignore[typeddict-item]
    assert terminal["size"] == SIZE + 4
    assert terminal["appended_data_base64"] == b64token
