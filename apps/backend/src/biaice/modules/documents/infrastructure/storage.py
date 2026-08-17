"""In-memory object store for M0; MinIO remains a later member-1 lockfile adapter."""

from __future__ import annotations

import hashlib
import threading


def locator_hash_for_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class InMemoryObjectStore:
    """Server-side blob map keyed by generated object keys, never browser URLs."""

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}
        self._locator_index: dict[str, str] = {}
        self._lock = threading.Lock()

    def put(self, key: str, data: bytes) -> str:
        locator = locator_hash_for_key(key)
        with self._lock:
            self._blobs[key] = data
            self._locator_index[locator] = key
        return locator

    def get(self, key: str) -> bytes | None:
        with self._lock:
            return self._blobs.get(key)

    def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._blobs

    def delete(self, key: str) -> bool:
        with self._lock:
            existed = self._blobs.pop(key, None) is not None
            locator = locator_hash_for_key(key)
            self._locator_index.pop(locator, None)
            return existed

    def key_for_locator(self, locator_hash: str) -> str | None:
        with self._lock:
            return self._locator_index.get(locator_hash)
