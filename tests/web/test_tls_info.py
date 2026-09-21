"""TLS client against a local TLS server and tool-level findings."""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from core.exceptions import NetworkError
from core.result import ResultStatus
from core.task import ExecutionContext
from infrastructure.network import TlsClient, TlsInfo
from modules.web.tls_info import TlsInfoTool


def _context() -> ExecutionContext:
    return ExecutionContext(
        task_id="t-tls",
        tool_id="web.tls_info",
        logger=logging.getLogger("tests.tls"),
        cancel_event=threading.Event(),
    )


def _make_certificate(
    tmp_path: Path,
    *,
    common_name: str = "localhost",
    san_dns: list[str] | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> tuple[Path, Path]:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    now = datetime.now(UTC)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(valid_from or (now - timedelta(days=1)))
        .not_valid_after(valid_to or (now + timedelta(days=30)))
    )
    if san_dns:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(name) for name in san_dns]),
            critical=False,
        )
    certificate = builder.sign(key, hashes.SHA256())
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


class _QuietHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def tls_server(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[str]:
    san = getattr(request, "param", ["localhost"])
    valid_from = datetime.now(UTC) - timedelta(days=2)
    valid_to = datetime.now(UTC) + timedelta(days=2)
    cert_path, key_path = _make_certificate(
        tmp_path,
        common_name=san[0],
        san_dns=san,
        valid_from=valid_from,
        valid_to=valid_to,
    )
    import ssl

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
    server = ThreadingHTTPServer(("127.0.0.1", 0), _QuietHandler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"https://localhost:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_tls_client_fields(tls_server: str) -> None:
    port = int(tls_server.rsplit(":", 1)[1])
    info = TlsClient(timeout=5.0, verify=False).get_tls_info("localhost", port)
    assert info.version in ("TLSv1.2", "TLSv1.3")
    assert info.cipher_name
    assert info.subject
    assert len(info.sha256_fingerprint) == 64
    assert info.self_signed is True
    assert info.hostname_match is True
    assert "localhost" in info.san_dns


def test_tool_with_local_tls_server(tls_server: str) -> None:
    client = TlsClient(timeout=5.0, verify=False)
    result = TlsInfoTool(client=client).run({"url": tls_server}, _context())
    assert result.status is ResultStatus.SUCCESS
    assert result.data[0]["version"] in ("TLSv1.2", "TLSv1.3")
    assert any(finding.title == "自签名证书" for finding in result.findings)


def test_tool_http_url_rejected() -> None:
    result = TlsInfoTool().run({"url": "http://example.com"}, _context())
    assert result.status is ResultStatus.FAILED
    assert result.summary == "TLS分析需要HTTPS URL。"


class FakeTlsClient:
    def __init__(self, info: TlsInfo) -> None:
        self._info = info

    def get_tls_info(self, host: str, port: int = 443) -> TlsInfo:
        return self._info


def _info(**overrides: object) -> TlsInfo:
    defaults: dict[str, object] = {
        "host": "example.com",
        "port": 443,
        "version": "TLSv1.3",
        "cipher_name": "TLS_AES_256_GCM_SHA384",
        "subject": "CN=example.com",
        "issuer": "CN=Example CA",
        "not_before": "2020-01-01T00:00:00+00:00",
        "not_after": "2035-01-01T00:00:00+00:00",
        "serial_number": "1234",
        "sha256_fingerprint": "a" * 64,
        "san_dns": ("example.com",),
        "chain_subjects": ("CN=example.com", "CN=Example CA"),
        "self_signed": False,
        "hostname_match": True,
    }
    defaults.update(overrides)
    return TlsInfo(**defaults)  # type: ignore[arg-type]


def test_expired_certificate_high() -> None:
    expired = _info(not_after="2020-01-01T00:00:00+00:00")
    result = TlsInfoTool(client=FakeTlsClient(expired)).run(
        {"url": "https://example.com"},
        _context(),
    )
    expired_finding = next(finding for finding in result.findings if finding.title == "证书已过期")
    assert expired_finding.severity.value == "HIGH"


def test_hostname_mismatch_high() -> None:
    mismatched = _info(hostname_match=False)
    result = TlsInfoTool(client=FakeTlsClient(mismatched)).run(
        {"url": "https://example.com"},
        _context(),
    )
    assert any(finding.title == "证书与主机名不匹配" for finding in result.findings)


def test_old_protocol_low() -> None:
    old = _info(version="TLSv1.1")
    result = TlsInfoTool(client=FakeTlsClient(old)).run(
        {"url": "https://example.com"},
        _context(),
    )
    assert any(finding.title == "协议版本较旧" for finding in result.findings)


def test_plain_http_port_tls_error() -> None:
    import socket

    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    try:
        with pytest.raises(NetworkError):
            TlsClient(timeout=2.0, verify=False).get_tls_info("127.0.0.1", port)
    finally:
        server.close()
