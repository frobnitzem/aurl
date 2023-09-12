import os, logging
from functools import cache
from pathlib import Path
from typing import Optional, Union, Tuple

from urllib.parse import urlparse, parse_qs, quote, unquote
_logger = logging.getLogger(__name__)

import aiohttp

from .taskmgr import runcmd

class URL:
    """Parsed URL object.

    Fully parse a string into URL components
    and validate against valid URL formats.
   
    Attributes:

    * scheme   : str
    * netloc   : str
    * path     : str
    * query    : {key:val}
    * fragment : str

    """
    def __init__(self, s : str, validate=True):
        ans = urlparse(s, scheme='', allow_fragments=True)
        
        # store metadata
        if ans.query != '':
            self.meta = f"?{ans.query}"
        else:
            self.meta = ''
        if ans.fragment != '':
            self.meta = f"{self.meta}#{ans.fragment}"

        self.scheme = unquote(ans.scheme)
        self.netloc = unquote(ans.netloc)
        assert '%2F' not in ans.path, "Invalid path."
        self.path = unquote(ans.path)
        if self.scheme != 'file': # remove leading '/' in paths
            if len(self.path) > 0 and self.path[0] == '/':
                self.path = self.path[1:]
        if len(ans.query) > 0:
            self.query = parse_qs(ans.query,
                              keep_blank_values=True,
                              strict_parsing=True,
                              errors="strict")
        else:
            self.query = {}
        self.fragment = unquote(ans.fragment)
        self.s = ans.geturl()
        if not validate:
            return
        try:
            self.validate()
        except AssertionError as e:
            raise AssertionError(f"Invalid URL format: {self.s} -- {e}")

    def with_scheme(self, scheme):
        return urlparse(self.s, scheme='', allow_fragments=True) \
                  . _replace(scheme=scheme) \
                  . geturl()

    def __repr__(self):
        return f"URL('{self.s}')"
    def __hash__(self):
        return hash(repr(self))
    def __eq__(a, b):
        return repr(a) == repr(b)
    def fullpath(self):
        if self.scheme == 'file':
            return self.path
        s = self.netloc
        if len(self.path) > 0:
            s += '/' + self.path
        return s
    def validate(url):
        absent = lambda x: len(getattr(url, x)) == 0
        # netloc, path, query, fragment
        if url.scheme in ['file', 'module', 'spack']:
            assert absent('query') and absent('fragment')
        elif url.scheme in ['git', 'result']:
            assert absent('query')
        elif url.scheme == 'https' or url.scheme == 'http':
            assert absent('fragment')
        elif url.scheme == 'bin':
            assert absent('query') and absent('fragment') and absent('path')
        else:
            raise AssertionError(f"Unknown URL scheme: url.scheme")

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

async def download_url(base, url, chunk_size = 1024**2):
    async with aiohttp.ClientSession() as session:
      async with session.get(url) as response:
        if response.status != 200:
            _logger.error("Download error on %s: received status %d",
                              url, response.status)
            return False
        ##print("Status:", response.status)
        ##print("Content-type:", response.headers['content-type'])
        ##html = await response.text()
        #data = await response.read()
        ##print(data)

        # TODO: consider https://pypi.org/project/aiofiles/
        base.parent.mkdir(exist_ok=True, parents=True)
        #async with aiofiles.open(dest, mode="wb") as f:
        with open(base, 'wb') as f:
          async for data in response.content.iter_chunked(chunk_size):
            #await f.write(data)
            f.write(data)
    return True

# https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(program : str) -> Optional[str]:
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ.get("PATH", "").split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

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

        spack = base / 'bin' / 'spack'
        if spack.exists():
            return spack
        return None

    spack = has_spack(os.environ.get('SPACK_MANAGER', None), 'spack')
    if spack:
        return spack

    spack = has_spack(os.environ.get('SPACK_ROOT', None))
    if spack:
        return spack

    ans = which('spack')
    if ans is not None:
        return Path(ans)

    return None

async def lookup_or_fetch(url : URL, hostname : str,
                          base : Path) -> Optional[Path]:
    # Resolve URL and download.
    #
    # Base is the location to store the final result
    # in the event a download is needed.
    # This function is responsible for running mkdir/etc.
    # to get to base.
    #
    # Returns a local path if the resource can be retrieved
    # successfully, or None if the resource cannot be downloaded.
    #
    # Handles the following URL types:
    #    - (http|https)://* - download with aiohttp
    #    - git://* - run git clone
    #    - spack://* - run spack install
    #    - file://* TODO - check multiple filesystems
    #    - result://* TODO - escalate to higher-level servers
    #
    ok, ans = await lookup_local(url, hostname)
    if not ok:
        return None
    if ans is not None:
        return ans
    _logger.info("Downloading %s", url)
    if url.scheme == 'http' or url.scheme == 'https':
        ok = await download_url(base, url.s)
        if ok:
            return base
        return None
    elif url.scheme == 'git':
        base.parent.mkdir(exist_ok=True, parents=True)
        #gurl = f"git@{url.netloc}:{url.path}"
        gurl = f"https://{url.netloc}/{url.path}.git"
        if url.fragment != '':
            ret = await runcmd('git', 'clone', '--branch', url.fragment,
                               gurl, base)
        else:
            ret = await runcmd('git', 'clone', gurl, base)
        if ret != 0:
            return None
        return base
    elif url.scheme == 'spack':
        spack = find_spack()
        if spack is None:
            return None

        ret = await runcmd(spack, 'install', '-y', url.fullpath())
        if ret != 0:
            return None
        ans = await runcmd(spack, 'find', '--format', '{prefix}',
                           url.fullpath(), ret=True)
        if isinstance(ans, int):
            return None
        return Path( ans.strip() ) / url.path
    elif url.scheme == 'file':
        if url.netloc == hostname or url.netloc == '':
            #return '/'+url.path
            ans = Path(url.path)
            if not ans.exists():
                return None
            return ans
        return None
    elif url.scheme == 'result':
        return None
    else:
        _logger.error("Unknown scheme, can't fetch: %s", url)
    return None

async def lookup_local(url : URL, hostname : str
                       ) -> Tuple[bool, Optional[Path]]:
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
    #  * (True, Path) on success
    #  * (True, None) if further lookup is needed
    #  * (False, None) if lookup is impossible
    # 
    def success(ans : Optional[Path]) -> Tuple[bool, Optional[Path]]:
        if ans is None:
            return (True, None)
        return (True, ans)
    fail = (False, None)
    if url.scheme == 'file':
        if url.netloc == hostname:
            ans = Path(url.path)
            if not ans.exists():
                return fail
            return success( ans )
        return success(None)
    elif url.scheme == 'bin':
        ans = await runcmd('which', url.netloc, ret=True)
        if isinstance(ans, int):
            return fail
        return success( Path(ans.strip()) )
    elif url.scheme == 'spack':
        spack = find_spack()
        if spack is None:
            return fail
        ans = await runcmd(spack, 'find', '--format', '{prefix}',
                           url.fullpath(), ret=True)
        if isinstance(ans, int):
            return success(None)
        return success( Path(ans.strip())/url.path )
    elif url.scheme == 'module':
        lmod = os.environ.get('LMOD_CMD', None)
        if lmod is None:
            return fail
        ans = await runcmd(lmod, "csh", "load", url.fullpath(), ret=True)
        if isinstance(ans, int):
            return fail

        prefix = parse_lmod_prefix(ans)
        if prefix is None:
            return fail
        return success( Path(prefix)/url.path )

    return success(None)
