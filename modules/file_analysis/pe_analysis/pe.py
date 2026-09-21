"""Static PE parsing wrapped around pefile (read-only, never executes samples)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pefile

from core.exceptions import FileSystemError, ToolInputError
from modules.file_analysis.entropy.analyzer import entropy_from_bytes

MACHINE_TYPES = {
    0x014C: "x86 (I386)",
    0x8664: "x64 (AMD64)",
    0x01C0: "ARM",
    0xAA64: "ARM64",
    0x01C4: "ARMNT",
}

SUBSYSTEMS = {
    1: "Native",
    2: "Windows GUI",
    3: "Windows CUI",
    9: "Windows CE GUI",
    10: "EFI Application",
}

IMPORT_CATEGORIES: dict[str, tuple[str, ...]] = {
    "Process": ("CreateProcess", "WinExec", "ShellExecute", "system", "exec"),
    "Memory": ("VirtualAlloc", "VirtualProtect", "HeapCreate", "WriteProcessMemory"),
    "Network": ("Internet", "socket", "connect", "URLDownload", "WinHTTP", "WinINet"),
    "File": ("CreateFile", "ReadFile", "WriteFile", "DeleteFile", "FindFirst"),
    "Registry": ("Reg", "Registry"),
    "Crypto": ("Crypt", "CryptEncrypt", "CryptDecrypt"),
    "System": ("GetProcAddress", "LoadLibrary", "GetModuleHandle"),
}


@dataclass(frozen=True, slots=True)
class PeImportEntry:
    dll: str
    name: str
    category: str


@dataclass(frozen=True, slots=True)
class PeAnalysisResult:
    machine: str
    bits: str
    timestamp: str
    entry_point: str
    image_base: str
    subsystem: str
    section_alignment: int
    file_alignment: int
    section_count: int
    characteristics: str
    dos_magic: str
    e_lfanew: str
    pe_signature: str
    sections: list[dict[str, Any]] = field(default_factory=list)
    imports: list[PeImportEntry] = field(default_factory=list)
    exports: list[dict[str, str]] = field(default_factory=list)
    resources: list[dict[str, str]] = field(default_factory=list)
    overlay_size: int = 0


def _timestamp(value: int) -> str:
    try:
        return datetime.fromtimestamp(value, UTC).isoformat()
    except (OverflowError, OSError, ValueError):
        return f"0x{value:08X}"


def _decode(value: bytes) -> str:
    return value.rstrip(b"\x00").decode("utf-8", errors="replace")


def _import_category(name: str) -> str:
    for category, keywords in IMPORT_CATEGORIES.items():
        if any(keyword.lower() in name.lower() for keyword in keywords):
            return category
    return "Other"


def analyze_pe(path: Path) -> PeAnalysisResult:
    """Parse a PE file; raises ToolInputError with a friendly message on failure."""
    try:
        pe = pefile.PE(str(path), fast_load=False)
    except pefile.PEFormatError as exc:
        raise ToolInputError("not a PE file", user_message="该文件不是有效的PE文件。") from exc
    except FileSystemError:
        raise
    except OSError as exc:
        raise FileSystemError(str(exc), user_message="无法读取文件。") from exc
    except Exception as exc:
        raise ToolInputError(
            f"PE parse failed: {exc}",
            user_message="无法解析PE文件。",
        ) from exc
    try:
        return _build_result(path, pe)
    finally:
        pe.close()


def _build_result(path: Path, pe: pefile.PE) -> PeAnalysisResult:
    file_header = pe.FILE_HEADER
    optional = pe.OPTIONAL_HEADER
    machine = MACHINE_TYPES.get(file_header.Machine, f"0x{file_header.Machine:04X}")
    bits = "64位" if optional.Magic == 0x20B else "32位"
    sections: list[dict[str, Any]] = []
    for section in pe.sections:
        data = section.get_data()
        sections.append(
            {
                "name": _decode(section.Name),
                "virtual_address": f"0x{section.VirtualAddress:08X}",
                "virtual_size": f"0x{section.Misc_VirtualSize:08X}",
                "raw_size": f"0x{section.SizeOfRawData:08X}",
                "pointer_to_raw": f"0x{section.PointerToRawData:08X}",
                "characteristics": f"0x{section.Characteristics:08X}",
                "executable": bool(section.Characteristics & 0x20000000),
                "writable": bool(section.Characteristics & 0x80000000),
                "entropy": round(entropy_from_bytes(data), 4) if data else 0.0,
            }
        )
    imports: list[PeImportEntry] = []
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            dll = entry.dll.decode("utf-8", errors="replace")
            for imported in entry.imports:
                name = (
                    imported.name.decode("utf-8", errors="replace")
                    if imported.name is not None
                    else f"ordinal {imported.ordinal}"
                )
                imports.append(PeImportEntry(dll=dll, name=name, category=_import_category(name)))
    exports: list[dict[str, str]] = []
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        for symbol in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            name = symbol.name.decode("utf-8", errors="replace") if symbol.name else "(unnamed)"
            exports.append(
                {
                    "ordinal": str(symbol.ordinal),
                    "name": name,
                    "address": f"0x{symbol.address:08X}",
                }
            )
    resources: list[dict[str, str]] = []
    if hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
            resource_type = getattr(entry, "name", entry.id)
            if hasattr(resource_type, "decode"):
                resource_type = str(resource_type)
            resources.append(
                {
                    "type": str(resource_type),
                    "id": str(entry.id),
                    "size": str((getattr(entry, "data", None) and entry.data.struct.Size) or 0),
                }
            )
    overlay_start = pe.get_overlay_data_start_offset() or path.stat().st_size
    overlay_size = max(0, path.stat().st_size - overlay_start)
    return PeAnalysisResult(
        machine=machine,
        bits=bits,
        timestamp=_timestamp(file_header.TimeDateStamp),
        entry_point=f"0x{optional.AddressOfEntryPoint:08X}",
        image_base=f"0x{optional.ImageBase:08X}",
        subsystem=SUBSYSTEMS.get(optional.Subsystem, str(optional.Subsystem)),
        section_alignment=optional.SectionAlignment,
        file_alignment=optional.FileAlignment,
        section_count=file_header.NumberOfSections,
        characteristics=f"0x{file_header.Characteristics:04X}",
        dos_magic="MZ",
        e_lfanew=f"0x{pe.DOS_HEADER.e_lfanew:08X}",
        pe_signature=f"0x{pe.NT_HEADERS.Signature:08X}",
        sections=sections,
        imports=imports,
        exports=exports,
        resources=resources,
        overlay_size=overlay_size,
    )
