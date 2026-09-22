from __future__ import annotations

import os
from collections.abc import Iterable

from .models import Proxy
from .pool import ProxyPool


class ProxyManager:
    def __init__(
        self,
        proxies: Iterable[Proxy] | None = None,
        *,
        host: str | None = None,
        ports: Iterable[int] | None = None,
        scheme: str = "http",
        username: str | None = None,
        password: str | None = None,
        cooldown: float = 2.0,
        failure_cooldown: float = 10.0,
        max_failure_cooldown: float = 300.0,
    ) -> None:
        if proxies is not None and (host is not None or ports is not None):
            raise ValueError("pass either proxies or host/ports, not both")

        if proxies is None:
            if not host:
                raise ValueError("host is required when proxies are not provided")
            if ports is None:
                raise ValueError("ports are required when proxies are not provided")
            proxies = (
                Proxy(
                    host=host,
                    port=int(port),
                    scheme=scheme,
                    username=username,
                    password=password,
                )
                for port in ports
            )

        self.pool = ProxyPool(
            proxies,
            cooldown=cooldown,
            failure_cooldown=failure_cooldown,
            max_failure_cooldown=max_failure_cooldown,
        )

    @classmethod
    def from_env(
        cls,
        *,
        host_var: str = "PROXY_HOST",
        ports_var: str = "PROXY_PORTS",
        default_host: str = "127.0.0.1",
        default_ports: Iterable[int] | None = None,
        **kwargs,
    ) -> "ProxyManager":
        host = os.getenv(host_var, default_host)
        raw_ports = os.getenv(ports_var)
        if raw_ports:
            ports = [int(value.strip()) for value in raw_ports.split(",") if value.strip()]
        elif default_ports is not None:
            ports = list(default_ports)
        else:
            raise ValueError(f"{ports_var} is not set and no default_ports were supplied")
        return cls(host=host, ports=ports, **kwargs)

    def acquire(self, *, timeout: float | None = None) -> Proxy:
        return self.pool.acquire(timeout=timeout)

    async def acquire_async(self, *, timeout: float | None = None) -> Proxy:
        return await self.pool.acquire_async(timeout=timeout)

    # Compatibility/convenience helpers.
    def get_proxy(self, *, timeout: float | None = None) -> dict[str, str]:
        return self.acquire(timeout=timeout).as_requests()

    async def get_proxy_async(self, *, timeout: float | None = None) -> dict[str, str]:
        return (await self.acquire_async(timeout=timeout)).as_requests()

    def get_proxy_selenium(self, *, timeout: float | None = None) -> str:
        return self.acquire(timeout=timeout).selenium

    async def get_proxy_selenium_async(self, *, timeout: float | None = None) -> str:
        return (await self.acquire_async(timeout=timeout)).selenium

    def report_success(self, proxy: Proxy) -> None:
        self.pool.report_success(proxy)

    def report_failure(self, proxy: Proxy) -> None:
        self.pool.report_failure(proxy)

    def state(self) -> list[dict[str, object]]:
        return self.pool.state()
