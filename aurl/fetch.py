from typing import Optional, Dict, Tuple, Union
import logging
_logger = logging.getLogger(__name__)

from pathlib import Path
import asyncio

import aiohttp

from .exceptions import DownloadException
from .urls import URL
from .search import which, lookup_local
from .runcmd import runcmd

async def download_url(outfile : Union[str, Path],
                       url : Union[str, URL], chunk_size = 1024**2):
    """ Download the url to the given output file.

        Raises a DownloadException on error.
    """
    out = Path(outfile)
    async with aiohttp.ClientSession() as session:
      async with session.get(str(url)) as response:
        if response.status != 200:
            raise DownloadException("Download error on %s: received status %d"%
                                    (url, response.status))
        ##print("Status:", response.status)
        ##print("Content-type:", response.headers['content-type'])
        ##html = await response.text()
        #data = await response.read()
        ##print(data)

        # TODO: consider https://pypi.org/project/aiofiles/
        out.parent.mkdir(exist_ok=True, parents=True)
        #async with aiofiles.open(dest, mode="wb") as f:
        with open(out, "wb") as f:
          async for data in response.content.iter_chunked(chunk_size):
            #await f.write(data)
            f.write(data)

async def lookup_or_fetch(url : URL, hostname : str, base : Path) -> Path:
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
    #    - git+(http|https|ssh)://* - run git clone
    #    - file://* TODO - check multiple filesystems
    #    - result://* TODO - escalate to higher-level servers
    #
    #
    # May throw a DownloadException
    #
    ans = await lookup_local(url, hostname)
    if ans is not None:
        return ans
    _logger.info("Attempting to download %s", url)
    if url.scheme == "http" or url.scheme == "https":
        return await download_url(base, url.s)
    elif url.scheme.startswith("git"):
        base.parent.mkdir(exist_ok=True, parents=True)
        gurl = url.s
        if gurl.startswith("git+"):
            gurl = gurl[4:]
        if '@' in url.s:
            gurl, commit = gurl.split('@', 1)
            ret, out, err = await runcmd("git", "clone", "--branch",
                                         commit, gurl, str(base))
        else:
            ret, out, err = await runcmd("git", "clone", gurl, str(base))
        if ret != 0:
            raise DownloadException(err)
        return base
    elif url.scheme == "file":
        if url.netloc == hostname or len(url.netloc) == 0:
            #return '/'+url.path
            ans = Path(url.path)
            if not ans.exists():
                raise DownloadException(f"Path does not exist: {url.s}")
            return ans
        # try to fetch remote file://?
        raise DownloadException(f"Unreachable {url.s}")
    elif url.scheme == "result":
        # These must be reached through a Mirror.
        raise DownloadException(f"Path does not exist: {url.s}")

    _logger.error("Unknown scheme, can't fetch: %s", url)
    raise DownloadException("Unknown scheme, can't fetch: %s"%url)
