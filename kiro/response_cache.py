# -*- coding: utf-8 -*-

"""
Response cache for Kiro Gateway.

Provides an in-memory LRU cache for API responses. When enabled, identical
requests (same model, messages, parameters) return cached results instead
of calling the Kiro API again.

Cache key is a SHA-256 hash of the canonicalized request payload.
Only non-streaming responses are cached.
"""

import hashlib
import json
import time
import threading
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

from loguru import logger


class ResponseCache:
    """Thread-safe LRU response cache with TTL.

    Attributes:
        max_size: Maximum number of cached entries.
        ttl: Time-to-live in seconds for each entry.
        enabled: Whether caching is active.
    """

    def __init__(
        self,
        max_size: int = 200,
        ttl: int = 3600,
        enabled: bool = False,
    ):
        """
        Initialize the response cache.

        Args:
            max_size: Maximum number of entries (LRU eviction).
            ttl: Seconds before an entry expires.
            enabled: Whether the cache starts enabled.
        """
        self.max_size = max_size
        self.ttl = ttl
        self.enabled = enabled
        self._cache: OrderedDict[str, Tuple[float, Dict[str, Any]]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _build_cache_key(request_data: Any) -> str:
        """
        Build a deterministic cache key from a request.

        Extracts model, messages, and generation parameters, then
        produces a SHA-256 hex digest.

        Args:
            request_data: Pydantic request model (ChatCompletionRequest
                          or AnthropicMessagesRequest).

        Returns:
            Hex digest string.
        """
        # Use model_dump for Pydantic v2, fall back to dict() for v1
        if hasattr(request_data, "model_dump"):
            payload = request_data.model_dump(exclude_none=True)
        else:
            payload = request_data.dict(exclude_none=True)

        # Remove fields that should not affect caching
        for key in ("stream", "stream_options", "user", "seed"):
            payload.pop(key, None)

        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get(self, request_data: Any) -> Optional[Dict[str, Any]]:
        """
        Look up a cached response.

        Args:
            request_data: The incoming request model.

        Returns:
            Cached response dict, or None on miss / disabled / expired.
        """
        if not self.enabled:
            return None

        key = self._build_cache_key(request_data)

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            ts, response = entry
            if time.time() - ts > self.ttl:
                # Expired
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Cache expired: {key[:12]}...")
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            logger.info(f"Cache hit: {key[:12]}...")
            return response

    def put(self, request_data: Any, response: Dict[str, Any]) -> None:
        """
        Store a response in the cache.

        Args:
            request_data: The request model (used to derive the key).
            response: The response dict to cache.
        """
        if not self.enabled:
            return

        key = self._build_cache_key(request_data)

        with self._lock:
            # Remove oldest if at capacity
            if key not in self._cache and len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            self._cache[key] = (time.time(), response)
            logger.debug(f"Cache stored: {key[:12]}... ({len(self._cache)}/{self.max_size})")

    def clear(self) -> int:
        """
        Clear all cached entries.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} entries removed")
            return count

    def stats(self) -> Dict[str, Any]:
        """
        Return cache statistics.

        Returns:
            Dict with size, max_size, hits, misses, hit_rate, enabled, ttl.
        """
        with self._lock:
            total = self._hits + self._misses
            return {
                "enabled": self.enabled,
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total > 0 else 0,
            }
