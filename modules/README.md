# Modules overview

本项目按模块组织工具能力，CTF 模块为编排层，其余模块提供能力：

- `network/`：IP 信息、Ping、TCP 连接/扫描、DNS、网络接口。
- `web/`：URL 解析、HTTP Header、Cookie、安全 Header、TLS、综合分析。
- `encoding/`：Base64/32/58、Hex、Binary、URL、Unicode、ROT、HTML Entity。
- `crypto/`：Hash、MD5 Reverse、XOR、JWT、RSA 辅助。
- `file_analysis/`：文件信息/类型/Hash/字符串/熵/Hex/PE/IOC/综合/批量。
- `system/`：系统信息、进程、连接、服务、启动项、用户、环境、监控、综合分析。
- `ctf/`：工作台编排（Auto Decode、Regex、Flag、Pipeline、Workspace 等）。

任务历史与报告中心位于 `core/history` 与 `core/reports`；插件系统位于
`core/plugin_sdk` / `core/plugin_manager`。

