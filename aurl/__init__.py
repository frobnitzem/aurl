from importlib.metadata import version, PackageNotFoundError
try:
    __version__ = version('aurl-aurl')
except PackageNotFoundError:
    __version__ = 'dev'

import asyncio

from .exceptions import DownloadException
from .urls import URL
from .template import Template, TemplateFile
from .mirror import Mirror

def arun(f):
    loop = asyncio.get_event_loop()
    ans = loop.run_until_complete(f)
    #loop.close()
    return ans

