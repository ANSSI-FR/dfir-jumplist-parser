"""Test with ptf2ref."""

import logging
import pathlib
import shutil
import tarfile
import tempfile
from io import BytesIO

import orjson

from jumplist_parser import parse_jumplist, setup_logging
from jumplist_parser.resolver import isoformat

DATA = pathlib.Path(__file__).parent / "resources" / "data.tar.xz"
DEFAULT_DATE = isoformat(1752845757)
logger = logging.getLogger(__name__)


def test_ptf2ref() -> None:
    """Try to run parser on every files."""
    if DATA.exists():
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir)
            try:
                logger.debug("Extracting ...")
                with tarfile.open(DATA) as tar:
                    tar.extractall(tmp_path, filter="data")

                for path in tmp_path.glob("**/*"):
                    if path.is_file():
                        data = path.read_bytes()
                        logger.debug("")
                        logger.debug("")
                        logger.debug(
                            "Size : %s , Filename : %s",
                            str(path.stat().st_size),
                            str(path.relative_to(tmp_path)),
                        )
                        with BytesIO(data) as unnamed_stream:
                            res = parse_jumplist(unnamed_stream, path)
                            fs = res["filesystem"]
                            if fs:
                                fs["path"] = str(path.relative_to(tmp_path))
                                fs["modification_time"] = DEFAULT_DATE
                                fs["access_time"] = DEFAULT_DATE
                                fs["creation_time"] = DEFAULT_DATE
                            json = orjson.dumps(
                                res,
                                option=orjson.OPT_INDENT_2,
                            ).decode("utf-8")
                            logger.debug("%s", json)
            finally:
                shutil.rmtree(tmp_path)
    else:
        error_message = f"Missing {DATA}"
        raise FileNotFoundError(error_message)


if __name__ == "__main__":
    setup_logging(None, "DEBUG")
    test_ptf2ref()
