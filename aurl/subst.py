"""Substitute a template file.
"""

__author__ = "David M. Rogers"
__copyright__ = "UT-Battelle LLC"
__license__ = "BSD3"

from pathlib import Path
import logging
_logger = logging.getLogger(__name__)

import typer

from .mirror import Mirror
from .template import TemplateFile
from .fetch import fetch_all, arun

app = typer.Typer()

@app.command(help="Fetch and substitute URLs into a template.")
def run(fname : str = typer.Argument(..., help="File name to substitute."),
        results : bool = typer.Option(False, "--results", help="list required results"),
        v     : bool = typer.Option(False, "-v", help="show info-level logs"),
        vv    : bool = typer.Option(False, "-vv", help="show debug-level logs"),
       ):
    if vv:
        logging.basicConfig(level=logging.DEBUG)
    elif v:
        logging.basicConfig(level=logging.INFO)

    fname = Path(fname)
    # remove last suffix
    out = fname.parent / fname.stem

    tf = TemplateFile(fname)
    urls = set(tf.uris)

    if results:
        for url in urls:
            if url.scheme == 'result':
                assert url.s[:9] == 'result://'
                print(url.s[9:])
                #print('git' + url.s[6:])
        return 0

    M = Mirror( Path() )
    lookup = arun(fetch_all(M, urls))
    if lookup is None:
        print("Unable to substitute.")
        return 1
    tf.write(out, lookup)

    return 0

if __name__ == "__main__":
    run()
