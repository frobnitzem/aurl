"""Get a list of URLs.
"""

__author__ = "David M. Rogers"
__copyright__ = "UT-Battelle LLC"
__license__ = "BSD3"

from typing import List, Optional
from pathlib import Path
import asyncio
import logging
_logger = logging.getLogger(__name__)

import typer
import json

from .mirror import Mirror
from .urls import URL
from . import arun

app = typer.Typer()

@app.command(help="Download a list of URLs.")
def get(urls   : List[str] = typer.Argument(..., help="urls to download"),
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
    urls1 = [URL(u) for u in urls]
    paths = arun(M.fetch_all(urls1))
    print(json.dumps(dict((k.s, str(v)) for k, v in paths.items()), indent=4))

if __name__=="__main__":
    get()
