"""Substitute a template file.
"""

__author__ = "David M. Rogers"
__copyright__ = "UT-Battelle LLC"
__license__ = "BSD3"

from pathlib import Path
from typing import Optional, List
import logging
_logger = logging.getLogger(__name__)

import typer

from .mirror import Mirror
from .template import TemplateFile
from .fetch import fetch_all, arun

app = typer.Typer()

@app.command(help="Fetch and substitute URLs into a template.")
def subst(templates  : List[str] = typer.Argument(..., help="File(s) to substitute."),
          results    : bool = typer.Option(False, help="Don't substitute, but list required results."),
          mirror     : Optional[Path] = typer.Option(None, help="directory holding downloaded files"),
          v     : bool = typer.Option(False, "-v", help="show info-level logs"),
          vv    : bool = typer.Option(False, "-vv", help="show debug-level logs"),
         ):
    if vv:
        logging.basicConfig(level=logging.DEBUG)
    elif v:
        logging.basicConfig(level=logging.INFO)

    if mirror is None:
        mirror = Path()

    urls = set()
    outputs = {}
    for fname1 in templates:
        fname = Path(fname1)
        # remove last suffix
        out = fname.parent / fname.stem
        if out in outputs:
            continue
        tf = TemplateFile(fname)
        urls |= set(tf.uris)
        outputs[out] = tf

    if results:
        for url in urls:
            if url.scheme == 'result':
                assert url.s[:9] == 'result://'
                print(url.s[9:])
                #print('git' + url.s[6:])
        return 0

    M = Mirror( mirror )
    ok, lookup = arun(fetch_all(M, urls))
    if not ok:
        print("Unable to substitute.")
        return 1
    tf.write(out, lookup)

    return 0

if __name__ == "__main__":
    subst()
