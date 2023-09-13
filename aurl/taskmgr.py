from typing import Optional, BinaryIO
import os

import asyncio
from typing import Awaitable, TypeVar
from typing import Generic, Sequence

from pathlib import Path

class TaskMgr:
    """Helper class for storing a list of tasks.

    Stores a list of tasks with optional additional info
    in its task-list.  On exit, all pending tasks
    are cancelled if they are not yet complete.

    The TaskMgr is iterable.  Note, however, that
    each loop will go through the tasks sequentially
    without replacement.  This means (loop..break) (loop)
    will not see the same set of tasks.

    Usage::
    
        import asyncio
        from aurl.taskmgr import TaskMgr
        with TaskMgr() as T:
           T.start(asyncio.sleep(1), 's1')
           T.start(asyncio.sleep(2), 's2')
           for t, name in T:
               await t
               print(f"{name} completed")
               break

    """
    def __init__(self):
        self.tasks = []
        #self.task_info = {}
        self.cur = 0 # next task to await completion (index into self.tasks)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        # (exc_type, exc, traceback) are *sys.exc_info()
        # or else None (on normal exit)
        for t in self.tasks: #[max(self.cur-1,0):]:
            if not t[0].done():
                t[0].cancel()
        return False # continue to raise the exception

    def start(self, c : Awaitable, *info):
        """Start the coroutine c as a task.
        
        Also stores its info for later retrieval.
        """
        #t = asyncio.create_task(c)
        t = asyncio.ensure_future(c)
        self.tasks.append((t,) + tuple(info))
        #self.task_info[t] = info

    def __iter__(self):
        return self

    def __next__(self):
        if self.cur == len(self.tasks):
            raise StopIteration
        tinfo = self.tasks[self.cur]
        self.cur += 1
        return tinfo

V = TypeVar('V')
class ResourceQueue(asyncio.Queue, Generic[V]):
    """Container for `n` parallel-accessible resources.

       Example:

           # start 3 client connections
           self.cq = ResourceQueue([ APIClient(config) for i in range(3) ])

           # Send a ping over the client connection.
           # Can be called concurrently.
           async def ping():
             async with ResourceContext(self.cq) as r:
                return await r.call("ping")
    """
    def __init__(self, resources : Sequence[V]):
        asyncio.Queue.__init__(self, len(resources))
        for r in resources:
            self.put_nowait( r )

class ResourceContext(Generic[V]):
    def __init__(self, cq : ResourceQueue[V]):
        self.cq = cq
    async def __aenter__(self) -> V:
        self.r = await self.cq.get()
        return self.r
    async def __aexit__(self, exc_type, exc, traceback):
        # (exc_type, exc, traceback) are *sys.exc_info()
        # or else None (on normal exit)
        await self.cq.put(self.r)
        return False # continue to raise the exception
