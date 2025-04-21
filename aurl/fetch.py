from typing import Optional, Dict, Tuple, Union
import logging
_logger = logging.getLogger(__name__)
import time

from pathlib import Path
import asyncio

import aiohttp
import aiofiles

from .exceptions import DownloadException
from .urls import URL
from .search import which, lookup_local
from .runcmd import runcmd

async def download_part(session: aiohttp.ClientSession, url: str, dest: str,
                        start: int, end: int, chunk_size: int) -> None:
    """ Download part of this URL using a Range header request
        between start and end (slice-like, 0-indexed, non-inclusive).

        Write the result to the destination file at the starting offset.
    """
    assert start >= 0 and end > start, "Invalid range"
    headers = {"Range": f"bytes={start}-{end-1}"}
    async with session.get(url, allow_redirects=True, headers=headers) as response:
        if response.status == 206:  # Partial Content
            async with aiofiles.open(dest, mode="r+b") as f:
                await f.seek(start)
                async for chunk in response.content.iter_chunked(chunk_size):
                    await f.write(chunk)
        else:
            raise DownloadException("Download error on %s (%d-%d): received status %d"%
                                    (url, start, end, response.status))

# try 1024**2 or 8192...
async def download_url(outfile: Union[str, Path],
                       url: Union[str, URL],
                       chunk_size: int = 1024**2,
                       max_connections: int = 4) -> int:
    """ Download the url to the given output file.

        Raises a DownloadException on error.

        Returns the downloaded file size (in bytes) on success.
    """
    assert chunk_size > 0 and max_connections > 0

    file_size: Optional[int] = None
    async with aiohttp.ClientSession() as session:
        async with session.head(url, allow_redirects=True) as response:
            if response.status == 200:
                file_size = int(response.headers.get('Content-Length', 0))

        if file_size is None:
            async with session.get(url, allow_redirects=True) as response:
                if response.status != 200:
                    raise DownloadException("%s: Error getting size (%d): %s",
                                            url, response.status, response.text())
                file_size = int(response.headers.get('Content-Length', 0))

        if file_size == 0:
            raise DownloadException("%s: File size is zero or not available.", url)

        dest = Path(outfile)

        dest.parent.mkdir(exist_ok=True, parents=True)
        # Create an empty file with the total size
        async with aiofiles.open(dest, mode="wb") as f:
            await f.seek(file_size - 1)
            await f.write(b'\0')

        chunks = (file_size+chunk_size-1)//chunk_size
        connections = min(chunks, max_connections)

        # note we always have chunks >= connections
        data_per_task = ( chunks // connections ) * chunk_size

        tasks = []
        for i in range(connections):
            start =   i * data_per_task
            end = start + data_per_task
            if i == connections-1:
                end = file_size  # Ensure the last part goes to the end
            task = asyncio.create_task(download_part(session, url, dest,
                                                     start, end, chunk_size))
            tasks.append(task)

        await asyncio.gather(*tasks)
    return file_size

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
        t0 = time.time()
        sz = await download_url(base, url.s)
        dt = time.time() - t0
        _logger.info("%s: %d bytes at %f Mbps", url, sz, sz*8/1024**2/dt)
        return base
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
