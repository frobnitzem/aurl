from typing import Optional, Dict, Tuple
from collections.abc import Iterable

from pathlib import Path
import asyncio

from .taskmgr import TaskMgr
from .urls import URL
from .mirror import Mirror

def arun(f):
    loop = asyncio.get_event_loop()
    ans = loop.run_until_complete(f)
    #loop.close()
    return ans

async def fetch_all(M : Mirror, urls : Iterable[URL],
                    verb=False) -> Tuple[bool, Dict[URL, Path]]:
    location : Dict[URL, Path] = {}
    ok = True
    with TaskMgr() as T:
        for url in set(urls):
            T.start(M.get(url), url)
        for t, url in T:
            path = await t
            if path is None:
                ok = False
                if verb:
                    print(f"{url.s} : Not found.")
            else:
                location[url] = path

    return ok, location

