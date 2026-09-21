# System security module（系统安全）

面向本机 Windows 的**只读**系统安全分析模块：信息收集 + 静态分析 + 状态查看。

## 工具

| 工具 | ID | 说明 |
| --- | --- | --- |
| 系统信息 | `system.system_info` | OS/CPU/内存/磁盘/运行时长 |
| 进程查看 | `system.processes` | 进程枚举（可搜索，单进程失败不影响列表） |
| 进程详细信息 | `system.process_detail` | 线程/命令行/工作目录/环境摘要 |
| 网络连接 | `system.connections` | TCP/UDP 连接与监听端口 |
| Windows 服务 | `system.services` | 状态/启动类型/映像路径（只读） |
| 启动项分析 | `system.startup` | Run/RunOnce 注册表键 + Startup 目录 |
| 用户与会话 | `system.users` | 当前登录会话（不读密码/凭据） |
| 环境信息 | `system.environment` | 环境变量，敏感值脱敏 |
| 资源监控 | `system.resource_monitor` | CPU/内存/网络速度采样序列 |
| 系统安全分析 | `system.analyzer` | 只读综合摘要（支持 PARTIAL） |

## 安全边界

- 全部只读：不结束进程、不启停/创建服务、不改注册表与启动项、不改账户/
  权限/防火墙/网络配置；修改型能力（如需）将单独规划为 Administrative/Advanced。
- Windows 能力封装在 `infrastructure/system` Provider 中；注册表仅 KEY_READ。
- 权限不足时局部显示 `[无法读取]`/Access Denied 并继续，不让整个分析失败。
- 命令行、Token、密码、敏感环境变量不写日志、不上传；所有分析本地完成。
- 结论均为事实/启发式提示：监听端口、启动项、PowerShell 命令等不等于恶意判定。

