"""Localhost-only fixtures shared by the integration tests.

No test in this package may touch the public internet; servers bind to
127.0.0.1 with an OS-assigned port.
"""

from __future__ import annotations

import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from core.app_context import AppContext
from modules import register_builtin_tools


class _Handler(BaseHTTPRequestHandler):
    """Tiny local server exposing the routes used by the web tools."""

    protocol_version = "HTTP/1.1"

    def do_HEAD(self) -> None:
        self._route(body=b"")

    def do_GET(self) -> None:
        self._route(body=b"integration-body")

    def _route(self, *, body: bytes) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/headers":
            self.send_response(200)
            self.send_header("Content-Security-Policy", "default-src 'self'")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/cookies":
            self.send_response(200)
            self.send_header("Set-Cookie", "session=secretvalue; HttpOnly; Secure; SameSite=Lax")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/404":
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/big":
            body = b"x" * (3 * 1024 * 1024)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command == "GET":
            self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class _QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request: object, client_address: object) -> None:
        # Broken pipes from the test client are expected; keep stderr clean.
        return


@pytest.fixture
def http_server() -> Iterator[str]:
    """Yield a base URL for the local HTTP fixture server."""
    server = _QuietServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = int(server.server_address[1])
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def tcp_ports() -> Iterator[tuple[int, int]]:
    """Yield an (open, closed) port pair bound to 127.0.0.1."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(4)
    open_port = int(server.getsockname()[1])

    def accept_loop() -> None:
        while True:
            try:
                connection, _ = server.accept()
            except OSError:
                return
            connection.close()

    thread = threading.Thread(target=accept_loop, daemon=True)
    thread.start()

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    closed_port = int(probe.getsockname()[1])
    probe.close()

    try:
        yield open_port, closed_port
    finally:
        server.close()
        thread.join(timeout=5)


@pytest.fixture
def context(tmp_home: Path) -> Iterator[AppContext]:
    """A fully wired application context with every built-in tool registered."""
    app = AppContext.create(load_plugins=False)
    register_builtin_tools(app.tool_registry)
    yield app
    app.shutdown()
