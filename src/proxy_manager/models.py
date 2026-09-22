from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote


@dataclass(frozen=True, slots=True)
class Proxy:
    host: str
    port: int
    scheme: str = "http"
    username: str | None = None
    password: str | None = None

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("proxy host must not be empty")
        if not 1 <= self.port <= 65535:
            raise ValueError("proxy port must be between 1 and 65535")
        if not self.scheme:
            raise ValueError("proxy scheme must not be empty")

    @property
    def key(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def url(self) -> str:
        auth = ""
        if self.username is not None:
            username = quote(self.username, safe="")
            password = quote(self.password or "", safe="")
            auth = f"{username}:{password}@"
        return f"{self.scheme}://{auth}{self.host}:{self.port}"

    @property
    def selenium(self) -> str:
        if self.username is None:
            return self.key
        return self.url

    def as_requests(self) -> dict[str, str]:
        return {"http": self.url, "https": self.url}

    def __str__(self) -> str:
        # Deliberately never expose credentials in logs.
        return f"{self.scheme}://{self.key}"
