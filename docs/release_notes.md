# Binary Alchemist Cyber Toolkit v1.0.0

发布日期：2026-09-21（以实际构建日期为准）

二进制炼金术士 · 网安工具箱 —— 面向 Windows 的桌面安全分析平台，用于安全
学习、CTF、实验环境与授权测试。

## 新增功能

- 完整桌面 GUI（深色/浅色主题、任务/日志/结果面板、窗口状态记忆）。
- 网络安全：IP 信息、Ping、TCP 连接检测、TCP 端口扫描、DNS、网络接口。
- Web 安全：URL 解析、HTTP Header、Cookie、安全 Header、TLS、HTTP 综合分析。
- 编码转换：Base64/32/58、Hex、Binary、URL、Unicode、ROT13/47、HTML Entity。
- 密码学：Hash、MD5 逆向分析（离线）、XOR、JWT、RSA 辅助。
- 文件分析：信息、类型识别、Hash、字符串、熵、Hex、PE、IOC、批量分析。
- 系统安全（只读）：系统信息、进程、连接、服务、启动项、用户、环境变量、
  资源监控、综合分析。
- CTF 工作台：工作区、Auto Decode、Regex、Flag、文本分析、模运算、
  数据转换、挑战分析器、笔记、本地流水线。
- 插件系统、任务历史与报告中心（SQLite 持久化）。

## 改进

- 全项目 582 项测试；core 覆盖率 93.5%，总体 87.6%。
- Ruff / MyPy strict 全绿；流式大文件处理；SQLite WAL + 索引验证。
- TCP 扫描进度批量化；Entropy C 级计数；打包体积精简。
- 首次启动欢迎页与安全说明、关于对话框、崩溃日志与友好错误提示。

## Bug 修复

- 任务面板插入新行后索引错位；导出 CSV 公式注入防护；损坏配置/数据库
  自动隔离恢复；窗口越界位置修正；报告模板在冻结包中的路径解析等。

## 已知问题

见 `docs/known_issues.md`（报告手动保存、Markdown 纯文本预览等低风险项）。

## 安装说明

- 方式 A（安装程序）：运行 `BinaryAlchemist-1.0.0-Setup.exe`，按向导安装。
  用户数据保存在 `%LOCALAPPDATA%\BinaryAlchemist`，卸载默认保留用户数据
  （可勾选删除）。
- 方式 B（便携版）：解压 `BinaryAlchemist-1.0.0-win64.zip`，运行
  `BinaryAlchemist.exe`。便携版数据跟随程序目录（内置 `portable.flag`）。
- 无需安装 Python。

## 安全说明

主动网络功能仅用于本机、实验室、CTF、靶场及经授权的测试目标。程序不
上传数据，不提供漏洞利用或隐蔽能力。

## 校验

文件 SHA256 见 `SHA256SUMS.txt`。
