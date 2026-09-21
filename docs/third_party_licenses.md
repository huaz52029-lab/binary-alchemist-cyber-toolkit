# 第三方依赖许可证

运行时与开发环境中的主要第三方依赖（版本为当前锁定环境的实测值）：

| 包 | 版本 | 许可证 | 用途 |
| --- | --- | --- | --- |
| PySide6 / shiboken6 | 6.11.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | GUI |
| pydantic / pydantic_core | 2.13.5 / 2.46.5 | MIT | 领域模型 |
| httpx | 0.28.1 | BSD-3-Clause | HTTP 客户端 |
| dnspython | 2.8.0 | ISC | DNS 查询 |
| cryptography | 50.0.1 | Apache-2.0 OR BSD-3-Clause | TLS/证书、RSA |
| pefile | 2024.8.26 | MIT | PE 解析 |
| psutil | 7.2.2 | BSD-3-Clause | 系统信息 |
| pywin32 | 312 | PSF | Windows 服务/注册表（只读） |
| certifi | 2026.7.22 | MPL-2.0 | CA 证书 |
| httpcore | 1.0.9 | BSD-3-Clause | httpx 底层 |
| h11 | 0.16.0 | MIT | HTTP/1.1 解析 |
| anyio | 4.15.1 | MIT | 异步基础 |
| idna | 3.20 | BSD-3-Clause | 域名 IDNA |
| cffi | 2.1.1 | MIT-0 | 原生绑定 |
| PyInstaller | 6.22.3 | GPLv2+（附自由分发例外） | 打包（开发） |
| pytest / pytest-cov | 9.1.1 / 7.1.0 | MIT | 测试（开发） |
| ruff | 0.16.8 | MIT | 静态检查（开发） |
| mypy / mypy_extensions | 2.3.1 / 1.1.0 | MIT | 类型检查（开发） |
| types-psutil / types-pywin32 | 见环境 | Apache-2.0 | 类型存根（开发） |

Qt 运行时随 PySide6 分发，采用其 LGPL/GPL 许可；本项目的 MIT 许可不变。
打包进 EXE 的依赖不改变其各自许可证。完整、权威的许可证文本以各包
发布页为准。
