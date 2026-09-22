# python-proxy-manager

Reusable proxy rotation for synchronous, threaded, and asyncio Python applications.

The package provides a shared proxy pool with:

- Round-robin proxy selection
- Per-proxy cooldown
- Thread-safe synchronous acquisition
- Asyncio-friendly acquisition
- Automatic exponential quarantine after failures
- Success/failure reporting
- Support for authenticated proxies
- Safe proxy labels that do not expose credentials
- Helpers for `requests` / `curl_cffi`, SeleniumBase, and other clients
- No runtime dependency on `requests`, `curl_cffi`, Selenium, or `aiohttp`

---

## Requirements

- Python 3.11+

---

## Installation

### Install from private GitHub repository

For normal usage in another project:

```bash
pip install "git+ssh://git@github.com/giorgos-tsak/python-proxy-manager.git"
```

This requires SSH access to the private GitHub repository.

To verify the installation:

```bash
python -c "import proxy_manager; print(proxy_manager.__file__)"
```

Then import it normally:

```python
from proxy_manager import ProxyManager
```

### Install a specific version

For production projects, prefer installing a specific Git tag:

```bash
pip install "git+ssh://git@github.com/giorgos-tsak/python-proxy-manager.git@v0.1.0"
```

This prevents a project from unexpectedly changing when `main` is updated.

### Install locally in editable mode

When developing the package locally:

```bash
pip install -e /path/to/python-proxy-manager
```

Windows example:

```powershell
pip install -e C:\Users\giorgos\python-proxy-manager
```

Changes made to the package source will immediately be available to the consuming environment.

### Install development dependencies

Inside the `python-proxy-manager` repository:

```bash
pip install -e ".[dev]"
```

This installs the package together with testing dependencies such as `pytest` and `pytest-asyncio`.

---

## Basic usage

```python
from proxy_manager import ProxyManager

manager = ProxyManager(
    host="127.0.0.1",
    ports=range(24004, 24019),
    cooldown=2.0,
)

proxy = manager.acquire()

print(proxy.host)
print(proxy.port)
print(proxy.url)
```

Example proxy:

```text
http://127.0.0.1:24004
```

The same `ProxyManager` instance should normally be reused throughout the application.

Avoid creating a new manager for every request, because rotation, cooldown, and failure state are maintained by the manager.

---

## Proxy formats

An acquired `Proxy` can be represented in several formats.

```python
proxy = manager.acquire()
```

### URL

```python
proxy.url
```

Example:

```text
http://127.0.0.1:24004
```

### Selenium

```python
proxy.selenium
```

Example:

```text
127.0.0.1:24004
```

### requests / curl_cffi

```python
proxy.as_requests()
```

Returns:

```python
{
    "http": "http://127.0.0.1:24004",
    "https": "http://127.0.0.1:24004",
}
```

---

## curl_cffi

```python
from curl_cffi import requests
from proxy_manager import ProxyManager

manager = ProxyManager(
    host="127.0.0.1",
    ports=range(24004, 24019),
    cooldown=2.0,
)

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

---

## Retrying with another proxy

A common scraping pattern is to quarantine a failed proxy and retry with another one.

```python
from curl_cffi import requests

def fetch(url: str):
    for attempt in range(3):
        proxy = manager.acquire()

        try:
            response = requests.get(
                url,
                proxies=proxy.as_requests(),
                impersonate="chrome",
                timeout=15,
            )

            response.raise_for_status()

        except Exception:
            manager.report_failure(proxy)

            if attempt == 2:
                raise

        else:
            manager.report_success(proxy)
            return response
```

When a proxy fails, `report_failure()` temporarily quarantines it. A subsequent `acquire()` can therefore select another available proxy.

---

## SeleniumBase

```python
from seleniumbase import SB
from proxy_manager import ProxyManager

manager = ProxyManager(
    host="127.0.0.1",
    ports=range(24004, 24019),
)

proxy = manager.acquire()

try:
    with SB(
        proxy=proxy.selenium,
        uc=True,
    ) as sb:
        sb.open("https://example.com")

except Exception:
    manager.report_failure(proxy)
    raise

else:
    manager.report_success(proxy)
```

---

## Async usage

Use `acquire_async()` inside asyncio applications:

```python
proxy = await manager.acquire_async()
```

Example:

```python
async def fetch(session, url: str):
    proxy = await manager.acquire_async()

    try:
        async with session.get(
            url,
            proxy=proxy.url,
        ) as response:
            response.raise_for_status()
            data = await response.text()

    except Exception:
        manager.report_failure(proxy)
        raise

    else:
        manager.report_success(proxy)
        return data
```

Async acquisition waits without blocking the event loop when all proxies are temporarily unavailable.

---

## ThreadPoolExecutor

A single manager can be shared between worker threads.

```python
from concurrent.futures import ThreadPoolExecutor

manager = ProxyManager(
    host="127.0.0.1",
    ports=range(24004, 24019),
    cooldown=2.0,
)

def worker(url):
    proxy = manager.acquire()

    try:
        # Perform request using proxy
        ...
    except Exception:
        manager.report_failure(proxy)
        raise
    else:
        manager.report_success(proxy)

with ThreadPoolExecutor(max_workers=15) as executor:
    executor.map(worker, urls)
```

The synchronous proxy pool is thread-safe.

---

## Authenticated proxies

You can create proxies that require a username and password:

```python
from proxy_manager import Proxy

proxy = Proxy(
    host="brd.superproxy.io",
    port=44445,
    username="username",
    password="password",
)
```

Or create a manager where every configured port uses the same credentials:

```python
manager = ProxyManager(
    host="brd.superproxy.io",
    ports=[44445],
    username="username",
    password="password",
)
```

Credentials are URL-encoded when constructing proxy URLs.

Avoid logging raw proxy URLs containing credentials.

---

## Environment configuration

The manager can optionally be constructed from environment variables.

```env
PROXY_HOST=127.0.0.1
PROXY_PORTS=24004,24005,24006,24007
```

Then:

```python
from proxy_manager import ProxyManager

manager = ProxyManager.from_env(
    cooldown=2.0,
)
```

You can also provide fallback ports:

```python
manager = ProxyManager.from_env(
    default_ports=range(24004, 24019),
    cooldown=2.0,
)
```

Environment configuration is optional. Applications can instead manage their own settings and pass them directly:

```python
manager = ProxyManager(
    host=settings.proxy_host,
    ports=settings.proxy_ports,
)
```

---

## Docker

When the proxy service runs on the host machine and the Python application runs inside Docker, the host may need to be changed.

Local:

```env
PROXY_HOST=127.0.0.1
```

Docker:

```env
PROXY_HOST=host.docker.internal
```

The application code can remain unchanged when using `ProxyManager.from_env()`.

---

## Cooldown

The normal cooldown controls how quickly the same proxy can be selected again:

```python
manager = ProxyManager(
    host="127.0.0.1",
    ports=range(24004, 24019),
    cooldown=2.0,
)
```

A proxy that has just been acquired will not be returned again until its cooldown has elapsed.

If every proxy is cooling down, `acquire()` waits until one becomes available.

An optional timeout can be supplied:

```python
proxy = manager.acquire(timeout=10)
```

Async:

```python
proxy = await manager.acquire_async(timeout=10)
```

---

## Failure quarantine

Failed proxies can be temporarily removed from rotation:

```python
manager.report_failure(proxy)
```

Successful proxies can be reset:

```python
manager.report_success(proxy)
```

Failure behavior can be configured:

```python
manager = ProxyManager(
    host="127.0.0.1",
    ports=range(24004, 24019),
    cooldown=2.0,
    failure_cooldown=10.0,
    max_failure_cooldown=300.0,
)
```

Repeated failures increase the quarantine duration exponentially up to `max_failure_cooldown`.

For example, with a 10-second base failure cooldown:

```text
Failure 1 -> 10 seconds
Failure 2 -> 20 seconds
Failure 3 -> 40 seconds
Failure 4 -> 80 seconds
...
Maximum   -> 300 seconds
```

A successful request resets the proxy's failure state.

---

## Pool state

Current proxy state can be inspected with:

```python
state = manager.state()

for proxy_state in state:
    print(proxy_state)
```

This can be useful for debugging, logging, or monitoring proxy health.

---

## Convenience methods

Instead of acquiring the `Proxy` object directly, several convenience methods are available.

### requests-style dictionary

```python
proxies = manager.get_proxy()
```

Async:

```python
proxies = await manager.get_proxy_async()
```

### Selenium string

```python
proxy = manager.get_proxy_selenium()
```

Async:

```python
proxy = await manager.get_proxy_selenium_async()
```

For code that needs failure reporting, prefer acquiring the `Proxy` object directly:

```python
proxy = manager.acquire()
```

This allows you to later call:

```python
manager.report_success(proxy)
manager.report_failure(proxy)
```

---

## Recommended application structure

A project can create one shared manager:

```text
my-project/
├── infrastructure/
│   └── proxies.py
├── scraper/
│   ├── mexc.py
│   └── gmgn.py
└── main.py
```

`infrastructure/proxies.py`:

```python
from proxy_manager import ProxyManager

proxy_manager = ProxyManager(
    host="127.0.0.1",
    ports=range(24004, 24019),
    cooldown=2.0,
)
```

Then use the same pool throughout the application:

```python
from infrastructure.proxies import proxy_manager

proxy = proxy_manager.acquire()
```

This ensures all workers share the same rotation, cooldown, and failure state.

---

## Testing

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run:

```bash
pytest
```

---

## Updating the package

When installed from GitHub, changes pushed to the repository do not automatically update existing environments.

Upgrade with:

```bash
pip install --upgrade "git+ssh://git@github.com/giorgos-tsak/python-proxy-manager.git"
```

For a specific release:

```bash
pip install --upgrade "git+ssh://git@github.com/giorgos-tsak/python-proxy-manager.git@v0.1.0"
```

For local editable installations, reinstalling is normally unnecessary because the environment points directly to the local source.

---

## Development workflow

Typical development workflow:

```text
1. Modify python-proxy-manager
2. Run pytest
3. Commit changes
4. Push to GitHub
5. Create a version tag when appropriate
6. Upgrade consuming projects to the new version
```

For active local development, prefer:

```bash
pip install -e /path/to/python-proxy-manager
```

For deployments and stable projects, prefer installing a tagged GitHub version.

---

## License

Private project. All rights reserved.