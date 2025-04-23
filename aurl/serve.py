# This stand-alone file server can be used in a pinch to
# serve a directory of files.  Note it serves everything under
# the directory you are running from!
#
# It supports HEAD queries and partial file downloads
# as used by aurl's parallel download methods.

import os, sys
from typing import Union
from pathlib import Path, PurePath

try: # fastapi is optional
    from fastapi import FastAPI, HTTPException, Response # type: ignore[import-not-found]
    from fastapi.responses import FileResponse # type: ignore[import-not-found]
    app = FastAPI()

    try: # improved logging is optional
        from certified.formatter import log_request # type: ignore[import-not-found]
        app.middleware("http")(log_request)
    except ImportError:
        pass

except ImportError: # These stubs will allow this module to load, but not work.
    class App(): # dummy app
        def get(self, *args, **kws):
            # empty decorator
            return lambda fn: fn
        def head(self, *args, **kws):
            # empty decorator
            return lambda fn: fn
    app = App() # type: ignore[assignment]
    class HTTPException(Exception): # type: ignore[assignment, no-redef]
        def __init__(self, status_code, detail):
            super().__init__(detail)

file_root = Path().resolve()

def safe_path(base: Path, fname: Union[Path,str]) -> Path:
    """Take an unsafe, user-provided fname, validate it,
    and place it relative to the base path.

    Throw an exception if the path contains ".." or is absolute.
    """

    rel = PurePath(fname)
    if rel.is_absolute() or ".." in rel.parts:
        raise HTTPException(status_code=403, detail="invalid path")

    if not base.is_dir():
        raise HTTPException(status_code=404, detail="base dir missing")

    # FIXME: check whether this path traverses a symlink
    # (https://stackoverflow.com/questions/41460434/getting-the-target-of-a-symbolic-link-with-pathlib)
    return base / rel

@app.get("/{filename:path}")
async def get_file(filename: str):
    """
    Serves a file from the working directory if it exists.
    """
    file_path = safe_path(file_root, filename)
    if file_path.is_file():
        return FileResponse(file_path, filename=file_path.name)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.head("/{filename:path}")
async def head_file(filename: str):
    """
    Handles HEAD requests for files in the working directory.
    Returns headers without the file body.
    """
    p = safe_path(file_root, filename)
    try:
        stat = p.stat()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")

    hdr = {
        "content-length": str(stat.st_size),
        "content-type": "application/octet-stream",
        "accept-ranges": "bytes",
        "content-disposition": f"attachment; filename={p.name}",
    }
    return Response(status_code=200, headers=hdr)
