# 配置说明

## 配置文件

- 出厂默认：`configs/default.json`（随程序分发，只读）。
- 用户覆盖：`data/config.json`（源码模式）或
  `%LOCALAPPDATA%\BinaryAlchemist\config.json`（发布模式）。
- 用户配置以深合并方式覆盖默认值；未知字段被忽略并告警；损坏的配置文件
  会被隔离为 `config.json.broken-<时间戳>` 并回退默认，程序不会因此崩溃。

## 常用设置

| 键 | 含义 | 默认 |
| --- | --- | --- |
| `theme` | `dark` / `light` | `dark` |
| `logging.level` | DEBUG/INFO/WARNING/ERROR/CRITICAL | `INFO` |
| `tasks.max_workers` | 全局后台任务并发上限（1-64，重启后生效） | `8` |
| `tasks.default_timeout` | 任务默认超时（秒） | `30` |
| `startup.load_plugins` | 启动时加载插件 | `false` |
| `recent_tools` | 最近使用工具 | `[]` |

主题、日志级别、并发上限、插件启动项也可在“设置”对话框修改。

## 目录策略

| 目录 | 用途 | 位置 |
| --- | --- | --- |
| `configs/` | 出厂配置、报告模板 | 程序目录（只读） |
| `data/` | 数据库、用户配置、结果 Artifact | 运行时根 |
| `logs/` | app.log / error.log / security.log（轮转 5MB×5） | 运行时根 |
| `plugins/` | 用户插件 | 运行时根 |
| `resources/` | 主题 QSS 与图标 | 程序目录（只读） |

运行时根（数据/日志/插件）的选择顺序：

1. 环境变量 `CYBERTOOLKIT_HOME`（最高优先级）。
2. 冻结发布：`%LOCALAPPDATA%\BinaryAlchemist`。
3. 冻结发布且 EXE 旁存在 `portable.flag`：EXE 所在目录（便携模式）。
4. 源码开发：仓库根目录。

## 日志

`logs/app.log`（全量）、`logs/error.log`（ERROR+）、`logs/security.log`
（安全事件）。日志只记录摘要，不记录完整环境变量、命令行、Cookie/Token 等
敏感内容。日志文件单文件 5MB、保留 5 个轮转副本。

## 数据库

`data/toolkit.db` 使用 WAL 模式与版本化迁移；损坏时会被隔离重建。历史与
报告共用同一数据库，结果 Artifact 位于 `data/results/`。
