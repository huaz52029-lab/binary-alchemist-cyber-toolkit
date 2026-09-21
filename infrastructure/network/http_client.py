"""Unified HTTP client built on httpx (GET/HEAD only, bounded and cancellable)."""

from __future__ import annotations

import ipaddress
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

from core import APP_NAME, APP_VERSION
from core.exceptions import DependencyMissingError, NetworkError, TaskCancelledError, ToolInputError

DEFAULT_TIMEOUT = 10.0
MAX_RESPONSE_BODY = 1024 * 1024
MAX_REDIRECTS = 10
USER_AGENT = f"{APP_NAME}/{APP_VERSION}"

SENSITIVE_HEADERS = {"authorization", "proxy-authorization", "cookie"}


@dataclass(frozen=True, slots=True)
class RedirectHop:
    url: str
    status_code: int
    location: str | None


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Normalized response captured by the unified client."""

    request_url: str
    method: str
    final_url: str
    status_code: int
    http_version: str
    headers: tuple[tuple[str, str], ...]
    body: bytes | None
    body_truncated: bool
    elapsed_seconds: float
    redirects: tuple[RedirectHop, ...]

    def header_values(self, name: str) -> list[str]:
        target = name.lower()
        return [value for key, value in self.headers if key.lower() == target]

    def first_header(self, name: str) -> str | None:
        values = self.header_values(name)
        return values[0] if values else None


def normalize_web_url(value: str) -> tuple[str, bool]:
    """Return an http(s) URL, prepending https:// when the scheme is missing."""
    stripped = value.strip()
    if not stripped:
        raise ToolInputError("empty url", user_message="请输入要分析的 URL。")
    split = urlsplit(stripped)
    scheme = split.scheme.lower()
    if "://" in stripped:
        if scheme not in ("http", "https"):
            raise ToolInputError(
                f"unsupported scheme: {scheme}",
                user_message="当前Web分析器只支持HTTP/HTTPS。",
            )
        return stripped, False
    if scheme:
        raise ToolInputError(
            f"unsupported scheme: {scheme}",
            user_message="当前Web分析器只支持HTTP/HTTPS。",
        )
    return f"https://{stripped}", True


def redact_header_value(name: str, value: str) -> str:
    """Mask sensitive header values; Set-Cookie is analyzed structurally instead."""
    if name.lower() in SENSITIVE_HEADERS:
        return "[REDACTED]"
    return value


def host_scope_note(host: str) -> str | None:
    """Return a note when the target is clearly local/private, or ``None``."""
    candidate = host.strip("[]").lower()
    if candidate in ("localhost", "localhost.localdomain") or candidate.endswith(".local"):
        return "目标属于本机/私有网络地址，请确认你拥有测试权限。"
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return None
    if address.is_private or address.is_loopback or address.is_link_local or address.is_unspecified:
        return "目标属于本机/私有网络地址，请确认你拥有测试权限。"
    return None


class HttpClient:
    """httpx wrapper exposing bounded GET/HEAD requests with redirect tracking."""

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        max_response_body: int = MAX_RESPONSE_BODY,
        max_redirects: int = MAX_REDIRECTS,
        user_agent: str = USER_AGENT,
        verify: bool = True,
    ) -> None:
        self._timeout = timeout
        self._max_response_body = max_response_body
        self._max_redirects = max_redirects
        self._user_agent = user_agent
        self._verify = verify
        self._logger = logging.getLogger("infra.network.http")

    def request(
        self,
        url: str,
        *,
        method: str = "GET",
        is_cancelled: Callable[[], bool] | None = None,
    ) -> HttpResponse:
        """Perform one GET/HEAD request with bounded body and redirect tracking."""
        normalized, _assumed = normalize_web_url(url)
        if method not in ("GET", "HEAD"):
            raise ToolInputError(
                f"unsupported method: {method}", user_message="仅支持 GET/HEAD 请求。"
            )
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise DependencyMissingError(
                "httpx is not installed",
                user_message="缺少 HTTP 依赖，请安装：pip install -e '.[network]'",
            ) from exc
        ssl_error_type = getattr(httpx, "SSLError", None)
        if is_cancelled is not None and is_cancelled():
            raise TaskCancelledError()
        started = time.perf_counter()
        try:
            with (
                httpx.Client(
                    timeout=self._timeout,
                    follow_redirects=True,
                    max_redirects=self._max_redirects,
                    verify=self._verify,
                    headers={"User-Agent": self._user_agent},
                ) as client,
                client.stream(method, normalized) as response,
            ):
                chunks: list[bytes] = []
                total = 0
                truncated = False
                for chunk in response.iter_bytes():
                    if is_cancelled is not None and is_cancelled():
                        raise TaskCancelledError()
                    remaining = self._max_response_body - total
                    if remaining <= 0:
                        truncated = True
                        break
                    if len(chunk) > remaining:
                        chunks.append(chunk[:remaining])
                        total += remaining
                        truncated = True
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                return HttpResponse(
                    request_url=normalized,
                    method=method,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    http_version=response.http_version,
                    headers=tuple((name, value) for name, value in response.headers.multi_items()),
                    body=b"".join(chunks),
                    body_truncated=truncated,
                    elapsed_seconds=time.perf_counter() - started,
                    redirects=tuple(
                        RedirectHop(
                            url=str(hop.url),
                            status_code=hop.status_code,
                            location=hop.headers.get("location"),
                        )
                        for hop in response.history
                    ),
                )
        except TaskCancelledError:
            raise
        except httpx.TimeoutException as exc:
            self._logger.warning("HTTP timeout for %s", normalized)
            raise NetworkError(
                "request timed out", user_message="请求超时，目标服务器未在时限内响应。"
            ) from exc
        except httpx.ConnectError as exc:
            self._logger.warning("HTTP connect error for %s: %s", normalized, exc)
            if ssl_error_type is not None and isinstance(exc, ssl_error_type):
                raise NetworkError(
                    "tls error",
                    user_message="TLS 验证失败：证书不受信任或与主机名不匹配。",
                ) from exc
            raise NetworkError("connect error", user_message="无法连接到目标服务器。") from exc
        except httpx.HTTPError as exc:
            self._logger.warning("HTTP error for %s: %s", normalized, exc)
            raise NetworkError("http error", user_message="HTTP 请求失败，请检查 URL。") from exc
