__author__ = "David M. Rogers"
__copyright__ = "UT-Battelle LLC"
__license__ = "BSD3"

from typing import List, Optional
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

@app.command(help="Get a directory structure served by aurl.serve.")
def get(url    : str = typer.Argument(..., help="directory tree root"),
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

    loc = arun(M.fetch(URL(f"{url}?max_depth=4")))
    if loc is None:
        print(f"Unable to download file listing for {url}")
        sys.exit(1)
    with loc.open() as f:
        tree = json.load(f)

    def add_tree(path, t, urls):
        for entry in t:
            name = f"{path}/{entry['name']}"
            if entry.children:
                if entry.children is True:
                    loc = M.fetch(f"{name}?max_depth=4")
                    if loc is None:
                        print(f"Unable to download file listing for {name}")
                        continue
                    with loc.open() as f:
                        tree = json.load(f)
                    add_tree(name, tree, urls)
                else:
                    add_tree(name, entry.children, urls)
                continue
            urls.append(URL(name))

    urls: List[URL] = []
    add_tree(url, tree, urls)
    paths = arun(M.fetch_all(urls))
    print(json.dumps(dict((k.s, str(v)) for k, v in paths.items()), indent=4))
    sys.exit(0)

if __name__=="__main__":
    get()
