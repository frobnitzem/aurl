from typing import Union, Tuple, Optional
import logging
_logger = logging.getLogger(__name__)

import asyncio
from pathlib import Path
from time import time as timestamp

async def runcmd(prog : Union[Path,str], *args : str,
                 cwd : Union[Path,str,None] = None,
                 expect_ok : Optional[bool] = True) -> Tuple[int,str,str]:
    """Run the given command inside an asyncio subprocess.
       
       Returns (return code : int, stdout : str, stderr : str)
    """
    pipe = asyncio.subprocess.PIPE
    proc = await asyncio.create_subprocess_exec(
                    str(prog), *args, cwd=cwd,
                    stdout=pipe, stderr=pipe)
    stdout, stderr = await proc.communicate()
    # note stdout/stderr are binary

    out = stdout.decode('utf-8')
    err = stderr.decode('utf-8')
    if len(stdout) > 0:
        _logger.debug('%s stdout: %s', prog, out)
    if len(stderr) > 0:
        _logger.info('%s stderr: %s', prog, err)

    ret = -1
    if proc.returncode is not None:
        ret = proc.returncode
    if expect_ok != (proc.returncode == 0):
        _logger.error('%s returned %d', prog, ret)
    if expect_ok is None:
        _logger.info('%s returned %d', prog, ret)

    return ret, out, err
