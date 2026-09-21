# Binary Alchemist Cyber Toolkit

二进制炼金术士 · 网安工具箱

A long-term maintained, extensible desktop security analysis platform for Windows,
built around clean architecture, a plugin system and a unified task/result model.

> This project is intended for security learning, CTF practice, lab environments and
> **authorized** security testing only. It does not ship destructive or stealthy
> capabilities. Never use it against systems you do not own or lack permission to test.

## Design goals

- Stable, low-coupling architecture with a strict dependency direction:
  `UI -> Application -> Domain`, `Infrastructure -> Domain`,
  `Modules -> Application / Domain / Infrastructure`.
- New tools are registered through metadata (`ToolDefinition`) and discovered by the
  `ToolRegistry`; adding a tool never requires editing the main window.
- Every long-running operation goes through the `TaskManager`
  (thread pool + cancellation + timeout + progress), never on the GUI thread.
- Every tool returns a unified `ToolResult` (status, summary, data, findings, logs,
  duration, metadata) and reports issues as structured `Finding` objects with an
  explicit fact / heuristic / risk classification.
- Minimal third-party dependencies: `pydantic` for the core models, with
  `PySide6`, `httpx`, `dnspython`, `cryptography`, `pefile` and `psutil` split into
  optional extras so each phase installs only what it needs.
- PyInstaller-ready path resolution (source checkout vs frozen bundle).

## Project status

Phases 0-4 (skeleton, core, GUI framework, first tool and the network module)
are complete. Packaging arrives in a later phase; see
[CHANGELOG.md](CHANGELOG.md) and the phase plan in [AGENTS.md](AGENTS.md).

## Available tools

Network security module (网络安全):

- **IP 信息分析器** (`network.ip_info`): analyze IPv4/IPv6 addresses and CIDR
  networks - version, network/broadcast addresses, netmask, prefix, address
  counts and scope attributes.
- **Ping 测试** (`network.ping`): system ICMP reachability and latency
  statistics (Windows icmp.dll backend).
- **TCP 连接检测** (`network.tcp_connect`): single TCP connect probe with
  OPEN/CLOSED/TIMEOUT/ERROR status.
- **TCP 端口扫描** (`network.tcp_scan`): bounded, cancellable TCP connect scan
  over a single port or a range, with progress and common-service hints.
- **DNS 查询** (`network.dns`): A/AAAA/CNAME/MX/NS/TXT/PTR/SOA records with
  human-readable error translation.
- **网络接口** (`network.interfaces`): local interface addresses, MAC, status,
  MTU and traffic counters.

Cryptography module (密码学):

- **Hash 计算器** (`crypto.hash`): MD5/SHA1/SHA224/SHA256/SHA384/SHA512 over
  text (UTF-8) or files (chunked), with case-insensitive comparison.
- **MD5 哈希逆向分析器** (`crypto.md5_reverse`): offline candidate verification,
  local dictionary matching and bounded charset brute-force search for MD5
  hashes; also exposed in the CTF category as MD5 Hash 分析 (`ctf.md5_reverse`).
- **XOR 工具** (`crypto.xor`): single-byte, brute-force scoring, repeating-key
  and equal-length hex XOR.
- **JWT 解析器** (`crypto.jwt`): offline header/payload decoding and claim
  analysis (no key guessing, no attacks).
- **RSA 辅助** (`crypto.rsa_helper`): n/e/d/p/q relationship analysis, φ(n) and
  d computation, plus PEM public key parsing.

Encoding module (编码转换):

- Base64 / Base32 / Base58 / Hex / Binary / URL Encode / Unicode / ROT13 / ROT47
  / HTML Entity (`encoding.*`): two-way text transforms with a shared workspace
  page (input, encode/decode, output, copy, swap, clear).

CTF module (CTF 工具):

- **Auto Decode** (`ctf.auto_decode`): bounded multi-layer candidate decoding
  (Base64/Base64URL/Base32/Base58/Hex/Binary/URL/Unicode/HTML/JSON/ROT/JWT/
  Gzip), with chain display, depth limits and cycle detection.
- **Regex 分析器** (`ctf.regex`): find/groups/replace with built-in templates
  and complexity hints.
- **Flag 提取** (`ctf.flag_tools`): candidate flag extraction with follow-up
  analysis.
- **Text Analysis** (`ctf.text_analysis`): statistics, frequency, entropy and
  encoding notes.
- **Crypto Helper** (`ctf.crypto_helper`): unified orchestration entry to the
  existing hash/XOR/RSA/Base64/Hex tools.
- **模数计算** (`ctf.mod_math`) and **数据转换** (`ctf.data_transform`).
- **CTF 工作台** (`ctf.workspace`), **CTF Notes** (`ctf.notes`) and
  **CTF Pipeline** (`ctf.pipeline`): local challenge workspaces, Markdown notes
  and local-only tool pipelines.
- **Challenge Analyzer** (`ctf.challenge_analyzer`): candidate classification
  with tool recommendations.

> The CTF module is an orchestration layer: it reuses the network/web/encoding/
> crypto/file/system tools rather than re-implementing them. Everything is
> offline and local; attachments are never executed; pipelines only run local
> tools and reject active network tools by default.

Plugin system (插件):

- Automatic discovery of one-level plugin folders under `plugins/`, validated
  `plugin.json` manifests (id, SemVer, API version, permissions, dependencies).
- Official Plugin SDK (`core.plugin_sdk`): `PluginContext`, `PluginConfigManager`,
  namespaced tool registration and lifecycle management (`PluginManager`).
- Plugin page in the GUI: list/enable/disable/refresh, details, tool opening;
  enable/disable persists across restarts; broken plugins are isolated.
- Bundled example plugin and a `templates/plugin_template/` plus
  `python scripts/create_plugin.py <name>` scaffolding.
- Full API docs in [docs/plugin_api.md](docs/plugin_api.md).

> Plugin code runs in-process with the same privileges as the application; it is
> not sandboxed. Only install trusted plugins. No online store, auto-download,
> dependency auto-install or remote execution is provided.

Web security module (Web安全):

- **URL 解析器** (`web.url_parser`): scheme/host/port/path/query/fragment and
  query parameters with sensitive-field notices.
- **HTTP Header 分析器** (`web.http_headers`): HEAD request (with recorded GET
  fallback) and full header table with sensitive-value redaction.
- **Cookie 安全分析** (`web.cookie_analysis`): Set-Cookie Secure/HttpOnly/
  SameSite attributes; values masked by default.
- **Web 安全 Header 检查** (`web.security_headers`): presence checks for nine
  common security headers with careful, fact-based findings.
- **TLS 信息分析** (`web.tls_info`): negotiated version, cipher, certificate,
  expiry and hostname verification (never bypasses verification).
- **HTTP 请求分析** (`web.http_analysis`): composite GET analysis combining
  headers, redirects, security headers, cookies, TLS and page metadata.

> The web module is for web security learning, site configuration review, labs,
> CTF practice and authorized testing. It performs plain GET/HEAD analysis only
> and ships no exploitation, payload generation, credential brute-force or
> stealth capabilities. Sensitive headers are redacted by default.

File analysis module (文件分析):

- **文件信息** (`file_analysis.file_info`): size, timestamps, attributes and
  magic-byte type detection with extension-mismatch notices.
- **文件 Hash** (`file_analysis.hashes`): MD5/SHA1/SHA2 in one streaming pass.
- **字符串提取** (`file_analysis.strings`): streaming ASCII/UTF-8/UTF-16LE
  strings with keyword hints.
- **文件熵分析** (`file_analysis.entropy`): Shannon entropy (0-8), with PE
  section-level entropy.
- **Hex Viewer** (`file_analysis.hex_viewer`): paged read-only hex dump with
  offset jump and ASCII/hex search.
- **PE 分析** (`file_analysis.pe_analysis`): DOS/NT headers, sections, imports,
  exports, resources and overlay.
- **IOC 候选提取** (`file_analysis.ioc`): candidate IPs/URLs/domains/emails/
  paths/registry keys.
- **文件安全分析** (`file_analysis.analyzer`): composite static analysis.
- **批量文件分析** (`file_analysis.batch`): bounded batch triage over files or
  directories with progress and cancellation.

> This module is strictly static: it reads, parses and displays files and never
> executes samples, loads DLLs, runs scripts or uploads files/hashes. High
> entropy, keyword hits, candidate IOCs and PE structure notes are analysis
> hints, never malware verdicts.

System security module (系统安全):

- **系统信息** (`system.system_info`): OS/CPU/memory/disk/boot-time overview.
- **进程查看** (`system.processes`): read-only process enumeration with search;
  per-process failures never break the list.
- **进程详细信息** (`system.process_detail`): threads, command line, cwd and
  environment summary for one PID.
- **网络连接** (`system.connections`): TCP/UDP connections and listening ports.
- **Windows 服务** (`system.services`): read-only service status, start type and
  image-path notes.
- **启动项分析** (`system.startup`): read-only Run/RunOnce registry keys and
  startup folders.
- **用户与会话** (`system.users`) and **环境信息** (`system.environment`, with
  sensitive-value redaction).
- **资源监控** (`system.resource_monitor`): sampled CPU/memory/network trends.
- **系统安全分析** (`system.analyzer`): composite read-only summary with
  partial-success support.

> This module is strictly read-only: it never terminates processes, stops or
> creates services, modifies the registry/startup items/accounts/firewall, or
> uploads any collected data. Permission limits degrade individual fields, not
> the whole analysis.

> MD5 is a one-way hash function. This tool searches user-provided candidate
> spaces for a matching value; it never queries online services, uploads hashes
> or performs online authentication brute-force.

> All encoding and cryptography tools run fully offline for security learning,
> CTF practice, data analysis and authorized testing; they never upload input
> text, tokens, hashes or files to any service.

> Network scanning is intended for local machines, lab environments, CTF
> practice, training ranges and **explicitly authorized** testing only. It
> performs TCP connect scans and never ships exploitation, fingerprinting or
> stealth capabilities.

## Requirements

- Windows 10/11
- Python 3.13.x

## Getting started

```powershell
# create a virtual environment (Python 3.13)
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1

# install core + development dependencies
python -m pip install -e ".[dev]"

# launch the desktop application
python main.py

# headless core self-check
python main.py --self-test
```

The GUI starts on a dark professional console theme with a left navigation tree,
dashboard statistics, live task/log panels and a settings dialog. Use
`--plugins` to load plugins from the plugins directory at startup.

Useful commands:

```powershell
python scripts\lint.py    # Ruff lint + format check
python -m mypy core       # static type check
python scripts\test.py    # pytest suite
```

## Layout

```text
main.py / app.py        thin entry point + application composition root
core/                   domain models, registry, task manager, config, logging, exporters
ui/                     PySide6 widgets (later phase)
modules/                security tool modules, grouped by category (later phases)
infrastructure/         adapters: network, filesystem, system providers (later phases)
configs/default.json    shipped default configuration
data/                   SQLite database + user config (runtime)
logs/                   app.log / error.log / security.log (runtime)
plugins/                user plugins (plugin.json + main.py)
tests/                  pytest suite, no external-network dependencies
scripts/                lint.py / test.py / build.py
```

## Configuration

Runtime configuration is JSON-based. Shipped defaults live in `configs/default.json`;
user overrides are written to `data/config.json`. Set `CYBERTOOLKIT_HOME` to relocate
the runtime data/logs/plugins directories. No configuration value is hard-coded in
business code, and sensitive values must never be persisted in plain text.

## Logging

All modules use the standard `logging` module through `core.logger`. Three rotating
files are maintained: `logs/app.log` (all levels), `logs/error.log` (ERROR+),
`logs/security.log` (security-relevant events). Log records carry task and tool ids
when available. `print` is forbidden in business code.

## Testing

```powershell
python scripts\test.py
```

Unit tests only exercise localhost and in-memory/temp fixtures; they never depend on
external internet access. Every core module ships with tests.

## License

[MIT](LICENSE)
