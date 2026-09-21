# IP 信息分析器（network.ip_info）

面向信息安全学习与授权的 IP 地址分析工具，也是本项目所有安全工具的参考模板。

## 功能

- 单个 IPv4 / IPv6 地址分析（裸地址按主机路由语义 `/32`、`/128` 分析）。
- IPv4 / IPv6 CIDR 网络分析（前缀、网络地址、总地址数、可用主机数）。
- 地址属性判定：私有 / 公网 / 回环 / 链路本地 / 组播 / 保留 / 未指定。
- IPv6 压缩形式与展开形式；IPv6 不展示广播地址（该语义不存在）。
- 结果统一为 `ToolResult`，通过 `TaskManager` 执行，可导出 JSON / TXT / CSV。

## 输入格式

```text
192.168.1.100        # 单个 IPv4
2001:db8::1          # 单个 IPv6
192.168.1.0/24       # IPv4 CIDR
2001:db8::/64        # IPv6 CIDR
```

输入会被 `strip()`；包含 `/` 时按接口/CIDR 处理，否则按单个地址处理。
空输入或无法解析的输入返回 `FAILED` 结果，UI 显示中文提示，不展示 traceback。

## 输出字段

`ToolResult.data[0]` 为一条 `IPInfoResult`：`input`、`input_type`、`address`、
`version`、`compressed`、`expanded`、`network`、`network_address`、
`broadcast_address`（IPv6 为 null）、`netmask`（IPv6 为 null）、`prefix_length`、
`total_addresses`、`usable_hosts`、`private`、`global`、`loopback`、`link_local`、
`multicast`、`reserved`、`unspecified`。

注意：属性取自 Python `ipaddress` 的语义。例如回环地址与链路本地地址的
`is_private` 也为真，组播地址的 `is_global` 也为真；因此界面与摘要按
“未指定 → 回环 → 组播 → 链路本地 → 保留 → 私有 → 公网”的优先级归纳，
避免把组播直接表述为“公网地址”等误导结论。

## 使用示例

```python
from modules.network.ip_info import IPInfoTool
from core.task_manager import TaskManager

manager = TaskManager(max_workers=4)
task_id = manager.submit_tool(IPInfoTool(), {"input": "192.168.1.0/24"})
snapshot = manager.wait(task_id, timeout=10)
print(snapshot.result.summary)
```

## 测试说明

`tests/network/test_ip_info.py` 覆盖 18 组解析用例、6 组非法输入、工具契约、
注册发现、TaskManager 执行与三种格式导出；`tests/ui/test_ip_info_page.py`
覆盖页面执行、错误展示与主窗口集成。全部测试不依赖外部网络。

