"""Test core module."""

from jumplist_parser import parse_jumplist
from tests.utils import LNK_PATH, run_as_daemon


def test_jumplist_parser() -> None:
    """Test the jumplist_parser function."""
    with LNK_PATH.open("rb") as stream:
        lnk = parse_jumplist(stream, LNK_PATH)
        assert lnk["status"] == "success"


def _parse_jumplist() -> None:
    with LNK_PATH.open("rb") as stream:
        lnk = parse_jumplist(stream, LNK_PATH)
        assert lnk["status"] == "success"


def test_daemon_without_multiprocessing() -> None:
    """Test if it can be run in daemon context (e.g. airflow dags)."""
    run_as_daemon(_parse_jumplist)
