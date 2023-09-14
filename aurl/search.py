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

@cache
def find_lmod() -> Optional[Path]:
    def has_lmod(s : Optional[str]) -> Optional[Path]:
        if s is None:
            return None
        lmod = Path(s)
        if os.access(lmod, os.X_OK):
            return lmod
        return None
    lmod = has_lmod(os.environ.get("LMOD_CMD", None))
    if lmod is not None:
        return lmod

    return which("lmod")

# Routines for resolving URL-s to resources.
#
def parse_lmod_prefix(vals : str) -> Optional[str]:
    # parse for setenv CMAKE_PREFIX_PATH /base/path;
    key = 'setenv CMAKE_PREFIX_PATH '
    n = len(key)
    for line in vals.split('\n'):
        if line.startswith(key):
            assert line[-1] == ';'
            return line[len(key):-1]
    # failing that, try the first path listed in these:
    keys = ['setenv PATH ', 'setenv LD_LIBRARY_PATH ']
    n = len(key)
    for line in vals.split('\n'):
        for key in keys:
            n = len(key)
            if line.startswith(key):
                assert line[-1] == ';'
                return str( Path(line[n:-1].split(':', 1)[0]).parent )
    return None

@cache
def find_spack() -> Optional[Path]:
    def has_spack(s : Optional[str], suffix : Optional[str] = None
                  ) -> Optional[Path]:
        if s is None:
            return None
        base = Path(s)
        if suffix is not None:
            base = base / suffix

        spack = base / "bin" / "spack"
        if os.access(spack, os.X_OK):
            return spack
        return None

    spack = has_spack(os.environ.get("SPACK_MANAGER", None), "spack")
    if spack:
        return spack

    spack = has_spack(os.environ.get("SPACK_ROOT", None))
    if spack:
        return spack

    return which("spack")

async def lookup_local(url : URL, hostname : str) -> Optional[Path]:
    # Note: Several of the lookups performed print
    #       error messages to stderr.  We do not
    #       capture these, but allow them to pass-through.
    #
    # Handles the following cases
    #    - file://{hostname}/*
    #    - bin://*
    #    - spack://*
    #    - module://*
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
    elif url.scheme == "bin":
        ans = which(url.fullpath())
        if ans is None:
            raise DownloadException(f"{url.s} does not exist locally")
        return ans
    elif url.scheme == "spack":
        spack = find_spack()
        if spack is None:
            raise DownloadException("spack not found")
        ret, out, err = await runcmd(spack, 'find', '--format', '{prefix}',
                                     url.fullpath())
        if ret != 0:
            _logger.info("Spack find %s failed with err: %s, output: %s",
                         url.fullpath(), err, out)
            return None
        return Path(out.strip().split("\n")[-1])
    elif url.scheme == "module":
        lmod = find_lmod()
        if lmod is None:
            raise DownloadException("lmod not found or LMOD_CMD not defined")
        ret, out, err = await runcmd(lmod, "csh", "load",
                                     url.fullpath())
        if ret != 0:
            raise DownloadException(err)

        prefix = parse_lmod_prefix(out)
        if prefix is None:
            raise DownloadException(f"no directory for module {url.fullpath()}")
        return Path(prefix)

    return None
