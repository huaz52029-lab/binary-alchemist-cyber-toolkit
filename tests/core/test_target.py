from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.exceptions import ToolInputError
from core.target import Target, TargetType, describe_cidr, is_private_address


def test_type_detection() -> None:
    assert Target(value="192.168.1.1").type is TargetType.IP_ADDRESS
    assert Target(value="2001:db8::1").type is TargetType.IP_ADDRESS
    assert Target(value="example.com").type is TargetType.HOSTNAME
    assert Target(value="https://example.com/x?y=1").type is TargetType.URL
    assert Target(value=r"C:\Windows\System32").type is TargetType.FILE


def test_private_and_loopback() -> None:
    assert Target(value="10.0.0.1").is_private
    assert not Target(value="8.8.8.8").is_private
    assert Target(value="127.0.0.1").is_loopback
    assert is_private_address("192.168.0.1")


def test_describe_cidr_ipv4() -> None:
    info = describe_cidr("192.168.1.0/28")
    assert info["network_address"] == "192.168.1.0"
    assert info["broadcast_address"] == "192.168.1.15"
    assert info["netmask"] == "255.255.255.240"
    assert info["host_count"] == 14
    assert info["first_host"] == "192.168.1.1"
    assert info["last_host"] == "192.168.1.14"
    assert info["is_private"] is True


def test_describe_cidr_invalid_raises() -> None:
    with pytest.raises(ToolInputError):
        describe_cidr("not-a-cidr")


def test_empty_target_rejected() -> None:
    with pytest.raises(ValidationError):
        Target(value="   ")
