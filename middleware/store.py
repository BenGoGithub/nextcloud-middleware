from __future__ import annotations

import uuid
from threading import Lock
from typing import Union

from cachetools import TTLCache

from middleware.models import EventOutput, TaskOutput


class PendingConfirmationStore:
    def __init__(self, maxsize: int = 256, ttl: int = 600) -> None:
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = Lock()

    def save(self, output: Union[TaskOutput, EventOutput]) -> str:
        request_id = str(uuid.uuid4())
        with self._lock:
            self._cache[request_id] = output
        return request_id

    def pop(self, request_id: str) -> Union[TaskOutput, EventOutput, None]:
        with self._lock:
            return self._cache.pop(request_id, None)


pending_store = PendingConfirmationStore()
