import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from proxy_manager import Proxy, ProxyManager, ProxyPool, proxy_label


def test_proxy_formats():
    proxy = Proxy("127.0.0.1", 24004)
    assert proxy.key == "127.0.0.1:24004"
    assert proxy.url == "http://127.0.0.1:24004"
    assert proxy.selenium == "127.0.0.1:24004"
    assert proxy.as_requests()["https"] == proxy.url


def test_credentials_are_encoded_and_hidden_from_label():
    proxy = Proxy("proxy.test", 1234, username="a@b", password="secret value")
    assert "a%40b:secret%20value@" in proxy.url
    assert "secret" not in str(proxy)
    assert proxy_label(proxy.url) == "http://proxy.test:1234"


def test_round_robin_without_cooldown():
    pool = ProxyPool([Proxy("localhost", 1), Proxy("localhost", 2)], cooldown=0)
    assert pool.acquire().port == 1
    assert pool.acquire().port == 2
    assert pool.acquire().port == 1


def test_failure_quarantines_proxy():
    pool = ProxyPool(
        [Proxy("localhost", 1), Proxy("localhost", 2)],
        cooldown=0,
        failure_cooldown=60,
    )
    first = pool.acquire()
    pool.report_failure(first)
    assert pool.acquire().port == 2


def test_manager_requests_adapter():
    manager = ProxyManager(host="127.0.0.1", ports=[24004], cooldown=0)
    assert manager.get_proxy() == {
        "http": "http://127.0.0.1:24004",
        "https": "http://127.0.0.1:24004",
    }


@pytest.mark.asyncio
async def test_async_acquire():
    manager = ProxyManager(host="127.0.0.1", ports=[24004], cooldown=0)
    proxy = await manager.acquire_async()
    assert proxy.port == 24004


def test_thread_safe_rotation():
    manager = ProxyManager(host="127.0.0.1", ports=range(24004, 24014), cooldown=0)
    with ThreadPoolExecutor(max_workers=10) as executor:
        ports = list(executor.map(lambda _: manager.acquire().port, range(100)))
    assert len(ports) == 100
    assert set(ports) == set(range(24004, 24014))
