# Network security module（网络安全）

## 工具

| 工具 | ID | 说明 |
| --- | --- | --- |
| IP 信息分析器 | `network.ip_info` | IPv4/IPv6 与 CIDR 分析 |
| Ping 测试 | `network.ping` | 系统 ICMP 连通性与延迟（Windows icmp.dll） |
| TCP 连接检测 | `network.tcp_connect` | 单端口 TCP 连通性 |
| TCP 端口扫描 | `network.tcp_scan` | 单端口/范围 TCP Connect 扫描 |
| DNS 查询 | `network.dns` | A/AAAA/CNAME/MX/NS/TXT/PTR/SOA |
| 网络接口 | `network.interfaces` | 本机接口地址/状态/流量 |

## 架构

每个工具遵循同一模板：`models.py`（输入/输出模型 + display spec）→ `tool.py`
（BaseTool 实现）→ 底层操作委托给 `infrastructure/network`（`TcpClient`、
`WindowsPingProvider`、`DnsClient`）与 `infrastructure/system`
（`NetworkInterfaceProvider`）。工具不直接 import socket / subprocess /
dnspython / psutil。所有耗时操作经 TaskManager 执行并支持取消，结果统一为
ToolResult 并可导出 JSON/TXT/CSV。

## 授权边界

仅用于本机、局域网实验环境、CTF、靶场及获得明确授权的测试目标。扫描工具只
提供 TCP 连通性检测，不含漏洞利用、指纹识别或隐蔽扫描能力。大范围扫描（超过
2048 个端口）会附加风险提示 Finding。

## 测试

`tests/network/` 下全部测试离线确定性：纯逻辑、localhost 临时服务器与
mock/injected provider；不依赖公网。DNS 依赖 dnspython（`[network]` extra），
Windows ICMP 回环测试仅在本机执行。

