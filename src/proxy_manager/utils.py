from __future__ import annotations

from urllib.parse import urlsplit

from .models import Proxy


def proxy_label(proxy: Proxy | dict[str, str] | str) -> str:
    if isinstance(proxy, Proxy):
        return str(proxy)
    if isinstance(proxy, dict):
        proxy_url = proxy.get("https") or proxy.get("http")
        return _safe_proxy_url(proxy_url) if proxy_url else "proxy"
    return _safe_proxy_url(proxy)


def _safe_proxy_url(proxy_url: str) -> str:
    candidate = proxy_url if "://" in proxy_url else f"//{proxy_url}"
    parsed = urlsplit(candidate)
    if not parsed.hostname:
        return "proxy"
    host = parsed.hostname
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return f"{parsed.scheme}://{host}" if parsed.scheme else host
