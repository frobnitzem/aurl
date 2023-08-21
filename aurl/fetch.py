from typing import Optional, Dict
from pathlib import Path
import asyncio

from .taskmgr import TaskMgr
from .urls import URL

def arun(f):
    loop = asyncio.get_event_loop()
    ans = loop.run_until_complete(f)
    loop.close()
    return ans

async def fetch_all(M, urls) -> Optional[Dict[URL, Path]]:
    location : Dict[URL, Path] = {}
    with TaskMgr() as T:
        for url in urls:
            T.start(M.get(url), url)
        for t, url in T:
            location[url] = await t

    # Check result and report all fetch errors.
    err = False
    for url, v in location.items():
        if v is None:
            print(f"{url.s} : Not found.")
            err = True
    if err:
        return None
    return location

