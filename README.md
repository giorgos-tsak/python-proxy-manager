# python-proxy-manager

Reusable proxy rotation for synchronous, threaded and asyncio Python applications.

## Install locally

```bash
pip install -e /path/to/python-proxy-manager
```

## Basic usage

```python
from proxy_manager import ProxyManager

manager = ProxyManager(
    host="127.0.0.1",
    ports=range(24004, 24019),
    cooldown=2,
)

proxy = manager.acquire()
```

### curl_cffi / requests-style clients

```python
from curl_cffi import requests

proxy = manager.acquire()
try:
    response = requests.get(
        "https://example.com",
        proxies=proxy.as_requests(),
        impersonate="chrome",
        timeout=15,
    )
    response.raise_for_status()
except Exception:
    manager.report_failure(proxy)
    raise
else:
    manager.report_success(proxy)
```

### SeleniumBase

```python
proxy = manager.acquire()

with SB(proxy=proxy.selenium, uc=True) as sb:
    ...
```

### Async code

```python
proxy = await manager.acquire_async()
```

## Environment configuration

```bash
PROXY_HOST=127.0.0.1
PROXY_PORTS=24004,24005,24006,24007
```

```python
manager = ProxyManager.from_env(cooldown=2)
```

## Behavior

- round-robin selection
- per-proxy cooldown
- thread-safe synchronous acquisition
- asyncio-friendly acquisition without blocking the event loop
- exponential failure quarantine
- success/failure reporting
- credential-safe log labels
- no dependency on requests, curl_cffi, Selenium, or aiohttp
