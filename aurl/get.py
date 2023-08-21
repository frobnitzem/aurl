from typing import List
from pathlib import Path

import logging
_logger = logging.getLogger(__name__)

import typer

from .mirror import Mirror
from .urls import URL
from .fetch import fetch_all, arun

app = typer.Typer()

@app.command()
def run(urls : List[str] = typer.Argument(..., help="urls to download"),
          v  : bool = typer.Option(False, "-v", help="show info-level logs"),
          vv : bool = typer.Option(False, "-vv", help="show debug-level logs")):
    if vv:
        logging.basicConfig(level=logging.DEBUG)
    elif v:
        logging.basicConfig(level=logging.INFO)

    M = Mirror( Path() )
    urls = [URL(u) for u in urls]
    arun(fetch_all(M, urls))
