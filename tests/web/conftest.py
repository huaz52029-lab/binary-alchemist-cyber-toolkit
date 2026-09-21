"""Local HTTP fixtures (no external network in tests)."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class _Handler(BaseHTTPRequestHandler):
    def do_HEAD(self) -> None:
        self._handle(include_body=False)

    def do_GET(self) -> None:
        self._handle(include_body=True)

    def _handle(self, include_body: bool) -> None:
        path = self.path
        if path == "/ok":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            if include_body:
                self.wfile.write(b"hello")
        elif path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.end_headers()
        elif path == "/chain":
            self.send_response(301)
            self.send_header("Location", "/redirect")
            self.end_headers()
        elif path == "/missing":
            self.send_response(404)
            self.end_headers()
        elif path == "/error":
            self.send_response(500)
            self.end_headers()
        elif path == "/headers":
            self.send_response(200)
            for name, value in [
                ("Content-Security-Policy", "default-src 'self'"),
                ("X-Frame-Options", "DENY"),
                ("X-Content-Type-Options", "nosniff"),
                ("Set-Cookie", "session=abc123; Secure; HttpOnly; SameSite=Lax; Path=/"),
                ("Set-Cookie", "theme=dark"),
            ]:
                self.send_header(name, value)
            self.end_headers()
        elif path == "/html":
            body = (
                '<html lang="zh"><head><title>测试页面</title>'
                '<meta name="description" content="页面描述">'
                '<meta name="robots" content="noindex">'
                '<meta property="og:title" content="OG 标题">'
                '<link rel="canonical" href="https://example.com/">'
                "</head><body>hi</body></html>"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if include_body:
                self.wfile.write(body)
        elif path == "/slow":
            time.sleep(2.0)
            self.send_response(200)
            self.end_headers()
            if include_body:
                self.wfile.write(b"done")
        elif path == "/big":
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            if include_body:
                self.wfile.write(b"x" * (2 * 1024 * 1024))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def web_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
