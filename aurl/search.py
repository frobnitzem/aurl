from typing import Optional
from functools import cache
from pathlib import Path
import os
import logging
_logger = logging.getLogger(__name__)

from .exceptions import DownloadException
from .urls import URL
from .runcmd import runcmd

# https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
@cache
def which(program : str) -> Optional[Path]:
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return Path(program)
    else:
        for path in os.environ.get("PATH", "").split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return Path(exe_file)

    return None

async def lookup_local(url : URL, hostname : str) -> Optional[Path]:
    # Note: Several of the lookups performed print
    #       error messages to stderr.  We do not
    #       capture these, but allow them to pass-through.
    #
    # Handles the following cases
    #    - file://{hostname}/*
    #
    # Returns:
    #  * Path on success
    #  * None if further lookup is needed
    # 
    # May throw a DownloadException if lookup is impossible
    #
    fail = (False, None)
    if url.scheme == "file":
        if url.netloc == hostname or len(url.netloc) == 0:
            p = Path(url.path)
            if not p.exists():
                raise DownloadException(f"{url.s} does not exist locally")
            return p
        return None

    return None
