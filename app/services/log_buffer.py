import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import Any


class LogBuffer:
    def __init__(self, max_lines: int = 5000) -> None:
        self._items: deque[dict[str, Any]] = deque(maxlen=max_lines)
        self._subscribers: set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def append(self, stream: str, server_id: str, line: str) -> None:
        item = {
            "type": "log",
            "stream": stream,
            "server_id": server_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "line": line.rstrip("\r\n"),
        }
        async with self._lock:
            self._items.append(item)
            subscribers = list(self._subscribers)

        for queue in subscribers:
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                pass

    def recent(self, limit: int = 300) -> list[dict[str, Any]]:
        normalized_limit = max(1, min(int(limit), len(self._items) or 1))
        return list(self._items)[-normalized_limit:]

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

