__author__ = "David M. Rogers"
__copyright__ = "UT-Battelle LLC"
__license__ = "BSD3"

from typing import List, Optional, Dict, Any
from pathlib import Path
import asyncio
import logging
import sys
_logger = logging.getLogger(__name__)

import typer
import json

from .mirror import Mirror
from .urls import URL
from . import arun

app = typer.Typer()

async def get_list(url: str, M: Mirror, max_depth: int = 3,
                   ignore_hidden: bool = True) -> List[URL]:
    loc = await M.fetch(URL(f"{url}?max_depth={max_depth}"))
    if loc is None:
        print(f"Unable to download file listing for {url}")
        sys.exit(1)
    with loc.open() as f:
        tree = json.load(f)

    async def add_tree(path: str, t: Dict[str,Any], urls: List[URL]):
        for name, entry in t.items():
            if name.startswith(".") and ignore_hidden:
                continue
            rel = f"{path}/{name}"
            tree = entry.get('children', False)
            if tree:
                if tree is True:
                    loc = await M.fetch(URL(f"{rel}?max_depth={max_depth}"))
                    if loc is None:
                        print(f"Unable to download file listing for {rel}")
                        continue
                    with loc.open() as f:
                        tree = json.load(f)
                await add_tree(rel, tree, urls)
                continue
            urls.append(URL(rel))

    urls: List[URL] = []
    await add_tree(url, tree, urls)
    return urls

@app.command(help="Get a directory structure served by aurl.serve.")
def get_dir(url    : str = typer.Argument(..., help="directory tree root"),
            mirror : Optional[Path] = typer.Option(None, help="directory holding downloaded files"),
            v    : bool = typer.Option(False, "-v", help="show info-level logs"),
            vv   : bool = typer.Option(False, "-vv", help="show debug-level logs")):
    if vv:
        logging.basicConfig(level=logging.DEBUG)
    elif v:
        logging.basicConfig(level=logging.INFO)
    if mirror is None:
        mirror = Path()

    M = Mirror( mirror )

    urls = arun( get_list(url, M) )
    paths = arun( M.fetch_all(urls) )
    print(json.dumps(dict((k.s, str(v)) for k, v in paths.items()), indent=4))
    sys.exit(0)

if __name__=="__main__":
    app()
