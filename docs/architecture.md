# 架构说明

## 分层与依赖方向

依赖方向严格单向：

```text
UI ──────────────► Application ──────────────► Domain (core)
Infrastructure ──► Domain
Modules ─────────► Application / Domain / Infrastructure
```

- `core/`：领域层。统一模型（`ToolResult` / `Finding` / `Task` / `ToolDefinition` /
  `Report`）、服务（`ToolRegistry` / `TaskManager` / `ConfigManager` /
  `LoggerManager` / 导出器）、历史与报告仓储、插件 SDK 契约。**不依赖 UI，不
  依赖 PySide6。**
- `infrastructure/`：底层适配器（网络 HTTP/TCP/Ping/DNS/TLS、文件系统流式
  读取、系统 Provider、MD5 Provider）。只依赖 `core`。
- `modules/`：业务工具。每个工具是 `BaseTool` 子类，声明 `ToolDefinition`
  元数据（id 必须带 `<category>.` 命名空间），实现
  `run(params, context) -> ToolResult`。不接触 Qt，不修改其他工具数据。
- `ui/`：PySide6 界面。工具页面、结果/任务/日志面板、历史/报告/插件页面由
  注册表驱动；`ui.bridge` 通过 Qt 信号桥接 TaskManager 与 Logger。
- `app.py` / `main.py`：组合根与入口。`AppContext` 一次性装配全部服务。

## 核心数据流

```text
ToolPage ──submit──► TaskManager（有界线程池）──► BaseTool.run
                          │ 取消/超时/进度/监听
                          ▼
                     ToolResult ──► ResultPanel（UI）
                          │
                          └─► TaskHistoryManager（SQLite，自动落库）
                                  └─► ReportManager（引用任务，生成报告）
```

- 每个任务都有 `ExecutionContext`：日志、进度、取消检查的唯一通道。
- 历史与报告共用 `data/toolkit.db`（WAL）；大结果溢出为
  `data/results/<task_id>.json`。
- 导出统一走 `ExportManager`，并默认经过 `SensitiveDataSanitizer` 脱敏。

## 插件

- 发现：`plugins/` 下一级目录，读取 `plugin.json` 元数据（仅 metadata）。
- 加载：只加载 enabled 插件，工具 id 由 `NamespacedTool` 加插件前缀，无法
  覆盖官方工具；坏插件隔离。
- 插件代码与主程序同进程、同权限运行（无沙箱），只能安装可信插件。

## 路径与数据

- 源码开发模式：数据在仓库根（`data/`、`logs/`、`plugins/`）。
- 冻结发布：`%LOCALAPPDATA%\BinaryAlchemist`；EXE 旁存在 `portable.flag`
  时切换为便携模式（数据在 EXE 旁）。
- `CYBERTOOLKIT_HOME` 环境变量可在两种模式下强制重定位运行时数据。

## 并发与线程

- GUI 线程只做交互；一切长任务经 `TaskManager`（默认 8 worker）。
- SQLite 采用“单 Repository 连接 + 线程锁”策略；历史与报告各持一个独立
  连接，配合 WAL 并发读写。
- 取消是协作式的：工具在步骤间调用 `context.raise_if_cancelled()`。
