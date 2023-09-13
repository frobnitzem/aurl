from typing import Optional, Union, Dict
from collections.abc import Iterable
from pathlib import Path
import socket
import logging
_logger = logging.getLogger(__name__)

from .exceptions import DownloadException
from .urls import URL
from .fetch import lookup_or_fetch
from .taskmgr import ResourceQueue, ResourceContext, TaskMgr

def gethostname():
    #fqdn = socket.getfqdn(socket.gethostname())
    return socket.gethostname()

class Mirror:
    """Manage a local cache of data located at path `base`.
    
    the layout is::

        `base`/
           encoded1/
               files-inside-encoded1
           encoded2/ (mirrored remote subtree)
               files-inside-encoded1
           encoded3 (mirrored remote file)
           ....
    
    Encode/decode work as follows:

    >>> from pathlib import Path
    >>> from aurl.mirror import Mirror
    >>> from aurl.urls import URL
    >>> base = Path('/cache')
    >>> C = Mirror( base )
    >>> src = URL('https://www.example.com/index.html')
    >>> str( C.encode(src) )
    '/cache/https/www.example.com/index.html'

    >>> C.decode(base / 'https/www.example.com/index.html')
    URL('https://www.example.com/index.html')

    >>> src = URL('git://spool/frobnitzem/dwork/README.md#v1')
    >>> str( C.encode(src) )
    '/cache/git/spool#v1/frobnitzem/dwork/README.md'

    >>> C.decode(base / 'git/spool#v1/frobnitzem/dwork/README.md')
    URL('git://spool/frobnitzem/dwork/README.md#v1')

    >>> src = URL('http://nevada/user?tango=alpha')
    >>> str( C.encode(src) )
    '/cache/http/nevada?tango=alpha/user'

    >>> C.decode(base / 'http/nevada?tango=alpha/user')
    URL('http://nevada/user?tango=alpha')
    """
    def __init__(self, base : Union[str, Path], nparallel : int = 10):
        self.hostname = gethostname()
        self.base = Path(base).resolve()
        assert self.base.is_dir()

        self.cq = ResourceQueue(list(range(nparallel)))

        #self.db = {} #: Mapping from url to local path
        ## scan for initial database contents
        #for x in self.base.iterdir():
        #    if not x.is_dir(): continue
        #    url = self.decode(x)
        #    self.db[url] = x

    def encode(self, url : URL) -> Path:
        # write the path where the given URL would be stored
        ans = self.base / url.scheme / (url.netloc+url.meta)

        path = url.path
        # remove leading '/'
        if len(path) > 0 and path[0] == '/':
            path = path[1:]
        if len(path) > 0:
            ans = ans / path

        return ans

    def decode(self, path : Path) -> Optional[URL]:
        # write the URL which the path links to
        try:
            suffix = path.relative_to(self.base)
        except ValueError:
            return None

        p = suffix.parts
        if len(p) < 2:
            return None
        scheme = p[0]
        loc = URL(p[1], False)
        try:
            ans = URL(f"{scheme}://{loc.path}/" + '/'.join(p[2:]) + loc.meta)
        except: # validation error
            return None
        return ans

    async def fetch(self, url : URL) -> Optional[Path]:
        """Handles url downloads.

        Args:
           url: the resource to lookup or fetch.

        Returns:
           A Path pointing at the local, cached version of the
           resource (or None if lookup & fetch was unsuccessful).
        """
        if not isinstance(url, URL):
            _logger.error("get received a non-URL input")
            return None

        out = self.encode(url)
        if out.exists():
            return out

        _logger.info("No local copy of %s exists, attempting fetch.", url)
        async with ResourceContext(self.cq) as r:
            return await lookup_or_fetch(url, self.hostname, out)

    async def fetch_all(self, urls : Iterable[URL]) -> Dict[URL, Path]:
        """ Fetch all urls from the given mirror.
            Returns a mapping from url to the path where it can
            be accessed locally.

            raises DownloadException on error.
        """
        location : Dict[URL, Path] = {}
        errors = []
        with TaskMgr() as T:
            for url in set(urls):
                T.start(self.fetch(url), url)
            for t, url in T:
                try:
                    location[url] = await t
                except DownloadException as e:
                    errors.append(str(e))
        if len(errors) > 0:
            raise DownloadException("Download errors:\n    "
                                    + "\n\n-   ".join(errors))

        return location

    def to_url(self, fname : Path) -> str:
        """Returns a URL representation of a local path.
        """
        return f"file://{self.hostname}{fname}"

#   def new_stem(self):
#       # create a new subdirectory to hold a subtree of
#       # data from a single source
#       return Path( mkdtemp(dir=self.path) )
