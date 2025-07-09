from typing import Optional
from pathlib import Path

import asyncio
from functools import wraps, partial
from urllib.request import urlretrieve

from .urls import URL

def async_wrap(func):
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)
    return run 

@async_wrap
def download_ftp(url: URL, path: Path) -> Optional[str]:
    try:
        out_path, headers = urlretrieve(str(url), str(path))
    except Exception as e:
        return str(e)
    return None
