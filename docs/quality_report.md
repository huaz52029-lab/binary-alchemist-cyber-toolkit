# 阶段 12 质量报告

Binary Alchemist Cyber Toolkit — 全项目测试、稳定性与质量验证

## 基本信息

- 项目版本：0.13.0（推荐发布候选版本：v1.0.0-rc1，未应用）
- 测试时间：2026-09-21
- 测试环境：Windows 11（build 10.0.26200）
- Python：3.13.14（CPython）
- GUI：PySide6 6.11.2（Qt 6.11.2）
- 打包：PyInstaller 6.22.3（onedir）

## 测试总量

| 项目 | 结果 |
| --- | --- |
| 测试总数 | 568 |
| 通过 | 568 |
| 失败 | 0 |
| 跳过 | 0 |
| 警告 | 0（以 `-W error` 验证通过） |

测试分层：

- `tests/core` / `network` / `web` / `encoding` / `crypto` / `file_analysis` /
  `system` / `ctf` / `plugins` / `history` / `ui`：既有单元与 GUI 测试。
- `tests/integration`：localhost HTTP/TCP fixture 上的完整链路测试
  （ToolRegistry → TaskManager → Tool → ToolResult → History → Exporter）。
- `tests/regression`：历史缺陷回归测试（任务生命周期竞态、CSV 注入、
  Artifact 路径逃逸、插件入口逃逸、报告模板路径）。
- `tests/performance`：TaskManager 100/500/1000 压力、500 工具注册、
  SQLite 并发写入与 10000 条历史、10 插件、100 报告、100MB 大文件流式处理。

## 覆盖率

使用 `coverage`（分支覆盖）：

| 范围 | 覆盖率 | 目标 |
| --- | --- | --- |
| 核心 `core` | 92% | ≥ 90% |
| 核心 + `infrastructure` + `modules` | 88% | ≥ 80% |
| 100% 覆盖文件数 | 110 | — |

关键模块：ToolRegistry 99%、PluginLoader 97%、Result 94%、
ConfigManager 93%、Sanitizer 91%、Logger 91%、History/Report 约 90%、
TaskManager 86%。

## 静态检查

- Ruff：`ruff check` 通过；`ruff format --check` 通过（333 个文件格式一致）。
- MyPy（strict，无 `type: ignore` 掩蔽）：231 个源文件（core/ui/modules/
  infrastructure/app/main/scripts）无问题。

## 稳定性验证

- TaskManager：100/500/1000 任务不丢失、ID 唯一、状态计数正确；
  提交即取消 / 完成后取消 / 失败后取消 / 64 任务同时完成 / 批量取消，
  最终状态均为 CANCELLED 且无状态错乱。
- 并发：16 线程 × 50 条历史并发写入无 `database is locked`、无丢失；
  History 与 Report 两个连接共享同一 WAL 库。
- 取消：TCP Scan、MD5 Reverse、批量文件分析、CTF Pipeline 均已有取消测试；
  TaskManager 层竞态测试覆盖取消时机边界。
- 100 次任务循环后线程数有界（≤ 基线 + 8）。
- 100MB 文件 Hash/Strings/Entropy/Hex 全部流式处理，Hash 峰值内存 < 64MB。
- HTTP 响应体有 1MB 上限（3MB 响应被截断，不无限读入）。
- 正则：检测到高复杂度模式且文本 > 4KB 时拒绝执行，避免灾难性回溯。

## 数据与配置恢复

- SQLite：数据库缺失 / 空文件正常创建；损坏数据库被隔离为
  `toolkit.db.corrupt-<时间戳>` 并重建，启动不崩溃；未来版本的
  `user_version` 不会被回退迁移。
- Artifact：缺失的结果文件返回空而非崩溃；删除任务时校验路径位于
  results 目录内，拒绝越界删除。
- 报告悬空引用渲染为显式“[缺失引用]”，不产生静默坏引用。
- 配置：缺失 / 空 / JSON 损坏 / 非对象 / 非法取值 / 旧版本字段均回退默认
  配置；坏文件被隔离为 `config.json.broken-<时间戳>`。

## 安全审查（静态）

- 未发现 `eval` / `exec` / `os.system` / `shell=True` / `pickle.loads` /
  `yaml.load`；Ping 的 subprocess 仅作为非 Windows 回退且参数为列表。
- SQL 全部参数化；排序 / DISTINCT 列名使用白名单。
- CSV 导出统一防护 Formula Injection（`=` `+` `-` `@` 前缀中和）。
- JSON/TXT/CSV 导出统一经 SensitiveDataSanitizer 脱敏。
- 插件入口受 `plugin.json` 模式约束 + 目录逃逸校验；插件资源路径校验越界。
- 线程审计：TaskManager（有界线程池）与 TCP Scan（受控并发）之外无自建线程。
- 日志只记摘要；不记录完整环境变量 / 命令行 / Cookie / Token。
- 文件分析严格静态：不执行样本、不加载 DLL、不上传 Hash/文件。

## 打包与发布

- `BinaryAlchemist.spec`：PyInstaller onedir；打包 configs / resources /
  report_templates / 包元数据；过滤环境路径中的 ICU / OpenSSL / UCRT DLL。
- `python scripts/build.py`：构建 + 自动运行打包内 `--smoke-test`。
- 冒烟测试：冻结 EXE 内 GUI（offscreen）、58 内置工具、插件动态加载
  （示例插件 → 59 工具）、History、Report、TaskManager、Exporter 全部通过。
- 干净环境测试：将 `dist/BinaryAlchemist` 复制到独立目录后运行
  `BinaryAlchemist.exe --smoke-test` 退出码 0，不依赖开发机 Python / 源码。
- Windows 中文/空格路径解析、UTF-8（中文/Emoji）SQLite/JSON/CSV/Markdown
  往返均通过测试。

## 已知问题

见 [docs/known_issues.md](known_issues.md)。全部为低风险遗留项，不阻断
阶段 12 核心质量门槛。

## 结论

核心质量门槛（Pytest、Ruff、MyPy、关键集成测试、Build Smoke Test）全部通过。
当前版本可标记为 Release Candidate；推荐版本号 v1.0.0-rc1（未自动应用）。
