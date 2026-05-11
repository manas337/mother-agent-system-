"""
Async File Locking Queue - Agents wait in queue for file access
"""

import asyncio
from typing import Dict, Optional
from pathlib import Path
from contextlib import asynccontextmanager


class AsyncFileQueue:
    """
    Per-file async lock queue. Agents writing to the same file
    naturally queue up and wait for their turn.
    """

    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, resource_path: str) -> asyncio.Lock:
        if resource_path not in self._locks:
            self._locks[resource_path] = asyncio.Lock()
        return self._locks[resource_path]

    async def acquire(self, resource_path: str) -> bool:
        lock = self._get_lock(resource_path)
        await lock.acquire()
        return True

    def release(self, resource_path: str):
        lock = self._locks.get(resource_path)
        if lock and lock.locked():
            lock.release()

    def release_all(self):
        for resource_path, lock in list(self._locks.items()):
            if lock.locked():
                lock.release()

    def cleanup(self):
        self.release_all()


class LockManager:
    """
    Async context manager for safe file access with agent queuing.
    """

    def __init__(self, lock_dir: str):
        self._lock_dir = Path(lock_dir) / ".locks"
        self._lock_dir.mkdir(parents=True, exist_ok=True)
        self._queue = AsyncFileQueue()

    @asynccontextmanager
    async def lock_resource(self, resource_path: str):
        await self._queue.acquire(resource_path)
        try:
            yield
        finally:
            self._queue.release(resource_path)

    def cleanup(self):
        self._queue.cleanup()
