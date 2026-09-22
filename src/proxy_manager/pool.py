from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Iterable

from .models import Proxy


class ProxyPool:
    """Thread-safe round-robin pool with per-proxy cooldown and failure quarantine."""

    def __init__(
        self,
        proxies: Iterable[Proxy],
        *,
        cooldown: float = 2.0,
        failure_cooldown: float = 10.0,
        max_failure_cooldown: float = 300.0,
    ) -> None:
        self._proxies = tuple(proxies)
        if not self._proxies:
            raise ValueError("proxies must not be empty")
        if cooldown < 0 or failure_cooldown < 0 or max_failure_cooldown < 0:
            raise ValueError("cooldowns must be >= 0")

        self.cooldown = float(cooldown)
        self.failure_cooldown = float(failure_cooldown)
        self.max_failure_cooldown = float(max_failure_cooldown)

        self._next_index = 0
        self._last_used = {proxy.key: 0.0 for proxy in self._proxies}
        self._blocked_until = {proxy.key: 0.0 for proxy in self._proxies}
        self._failures = {proxy.key: 0 for proxy in self._proxies}
        self._lock = threading.Lock()

    @property
    def proxies(self) -> tuple[Proxy, ...]:
        return self._proxies

    def _wait_for_locked(self, proxy: Proxy, now: float) -> float:
        cooldown_until = self._last_used[proxy.key] + self.cooldown
        available_at = max(cooldown_until, self._blocked_until[proxy.key])
        return max(0.0, available_at - now)

    def try_acquire(self) -> tuple[Proxy | None, float]:
        """Return an available proxy, or (None, seconds_until_soonest_available)."""
        with self._lock:
            now = time.monotonic()
            shortest_wait = float("inf")

            for _ in self._proxies:
                proxy = self._proxies[self._next_index]
                self._next_index = (self._next_index + 1) % len(self._proxies)
                wait = self._wait_for_locked(proxy, now)
                if wait <= 0:
                    self._last_used[proxy.key] = now
                    return proxy, 0.0
                shortest_wait = min(shortest_wait, wait)

            return None, shortest_wait

    def acquire(self, *, timeout: float | None = None) -> Proxy:
        started = time.monotonic()
        while True:
            proxy, wait = self.try_acquire()
            if proxy is not None:
                return proxy

            if timeout is not None:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError("timed out waiting for an available proxy")
                wait = min(wait, remaining)

            time.sleep(max(0.001, wait))

    async def acquire_async(self, *, timeout: float | None = None) -> Proxy:
        started = time.monotonic()
        while True:
            proxy, wait = self.try_acquire()
            if proxy is not None:
                return proxy

            if timeout is not None:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError("timed out waiting for an available proxy")
                wait = min(wait, remaining)

            await asyncio.sleep(max(0.001, wait))

    def report_success(self, proxy: Proxy) -> None:
        with self._lock:
            self._validate(proxy)
            self._failures[proxy.key] = 0
            self._blocked_until[proxy.key] = 0.0

    def report_failure(self, proxy: Proxy) -> None:
        with self._lock:
            self._validate(proxy)
            failures = self._failures[proxy.key] + 1
            self._failures[proxy.key] = failures
            penalty = min(
                self.failure_cooldown * (2 ** (failures - 1)),
                self.max_failure_cooldown,
            )
            self._blocked_until[proxy.key] = time.monotonic() + penalty

    def state(self) -> list[dict[str, object]]:
        with self._lock:
            now = time.monotonic()
            return [
                {
                    "proxy": str(proxy),
                    "failures": self._failures[proxy.key],
                    "available_in": round(self._wait_for_locked(proxy, now), 3),
                }
                for proxy in self._proxies
            ]

    def _validate(self, proxy: Proxy) -> None:
        if proxy.key not in self._last_used:
            raise ValueError(f"unknown proxy: {proxy}")
