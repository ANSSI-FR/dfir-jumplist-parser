"""Module for errors."""


class JumpListError(Exception):
    """Base class exception."""


class MagicBytesError(JumpListError):
    """Raise when magic bytes do not match excepted one."""


class NotAnAutomaticDestinationError(MagicBytesError):
    """Raise when file is not an OLE."""


class NotACustomDestinationError(MagicBytesError):
    """Raise when first information are not valid for a custom destination."""


class NotALNKError(MagicBytesError):
    """Do not match lnk header."""


class UnparsableJumpListError(JumpListError):
    """Cannot parse Jumplist."""
