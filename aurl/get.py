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

from .mirror import Mirror
from .urls import URL
from .fetch import fetch_all, arun

app = typer.Typer()

@app.command(help="Download a list of URLs.")
def get(urls : List[str] = typer.Argument(..., help="urls to download"),
          v  : bool = typer.Option(False, "-v", help="show info-level logs"),
          vv : bool = typer.Option(False, "-vv", help="show debug-level logs")):
    if vv:
        logging.basicConfig(level=logging.DEBUG)
    elif v:
        logging.basicConfig(level=logging.INFO)

    M = Mirror( Path() )
    urls1 = [URL(u) for u in urls]
    ok, paths = arun(fetch_all(M, urls1, verb=True))
    if not ok:
        print("Unable to fetch all paths.")
        typer.Exit(1)

if __name__=="__main__":
    get()
