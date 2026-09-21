"""TLS handshake inspection built on ``ssl`` plus certificate parsing via cryptography."""

from __future__ import annotations

import fnmatch
import socket
import ssl
from dataclasses import dataclass
from typing import Any

from core.exceptions import DependencyMissingError, NetworkError, ToolInputError


@dataclass(frozen=True, slots=True)
class TlsInfo:
    host: str
    port: int
    version: str
    cipher_name: str
    subject: str
    issuer: str
    not_before: str
    not_after: str
    serial_number: str
    sha256_fingerprint: str
    san_dns: tuple[str, ...]
    chain_subjects: tuple[str, ...]
    self_signed: bool
    hostname_match: bool


class TlsClient:
    """Connects over TLS and extracts negotiated parameters and certificate data."""

    def __init__(self, *, timeout: float = 10.0, verify: bool = True) -> None:
        self._timeout = timeout
        self._verify = verify

    def get_tls_info(self, host: str, port: int = 443) -> TlsInfo:
        if not host.strip():
            raise ToolInputError("empty host", user_message="请输入 HTTPS 主机。")
        context = ssl.create_default_context() if self._verify else ssl._create_unverified_context()
        try:
            with (
                socket.create_connection((host, port), timeout=self._timeout) as raw,
                context.wrap_socket(raw, server_hostname=host) as tls_socket,
            ):
                chain = tls_socket.get_unverified_chain()
                parsed = self._parse_chain(chain, host)
                version = tls_socket.version() or "unknown"
                cipher = tls_socket.cipher()
                return TlsInfo(
                    host=host,
                    port=port,
                    version=version,
                    cipher_name=cipher[0] if cipher else "unknown",
                    **parsed,
                )
        except TimeoutError as exc:
            raise NetworkError("tls timeout", user_message="TLS 连接超时。") from exc
        except ssl.SSLCertVerificationError as exc:
            raise NetworkError(
                "certificate verification failed",
                user_message="TLS 证书验证失败（证书不受信任或与主机名不匹配）。",
            ) from exc
        except ssl.SSLError as exc:
            raise NetworkError(
                "tls handshake failed",
                user_message="TLS 握手失败，目标可能不支持 HTTPS。",
            ) from exc
        except socket.gaierror as exc:
            raise NetworkError("dns failure", user_message="域名解析失败，请检查主机名。") from exc
        except OSError as exc:
            raise NetworkError("tls connect error", user_message="无法建立 TLS 连接。") from exc

    @staticmethod
    def _parse_chain(chain: list[bytes], host: str) -> dict[str, Any]:
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes
            from cryptography.x509.oid import NameOID
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise DependencyMissingError(
                "cryptography is not installed",
                user_message="缺少 cryptography 依赖，请安装：pip install -e '.[crypto]'",
            ) from exc
        certificates = [x509.load_der_x509_certificate(der) for der in chain]
        if not certificates:
            raise NetworkError("empty certificate chain", user_message="未获取到证书链。")
        leaf = certificates[0]
        san_dns: list[str] = []
        try:
            san = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            san_dns = san.value.get_values_for_type(x509.DNSName)
        except x509.ExtensionNotFound:
            pass
        common_names = leaf.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        candidates = san_dns or [str(common_name.value) for common_name in common_names]
        hostname_match = any(fnmatch.fnmatchcase(host, candidate) for candidate in candidates)
        return {
            "subject": leaf.subject.rfc4514_string(),
            "issuer": leaf.issuer.rfc4514_string(),
            "not_before": leaf.not_valid_before_utc.isoformat(),
            "not_after": leaf.not_valid_after_utc.isoformat(),
            "serial_number": format(leaf.serial_number, "x"),
            "sha256_fingerprint": leaf.fingerprint(hashes.SHA256()).hex(),
            "san_dns": tuple(san_dns),
            "chain_subjects": tuple(
                certificate.subject.rfc4514_string() for certificate in certificates
            ),
            "self_signed": leaf.issuer == leaf.subject,
            "hostname_match": hostname_match,
        }
