# 性能基准（阶段 13 优化前）

所有数值来自本机真实运行，环境：Windows 11（10.0.26200）、Python 3.13.14、
CPython、SSD。可复现脚本：`python scripts/bench.py`。

## 启动（冷启动，offscreen GUI）

| 步骤 | 耗时 |
| --- | --- |
| AppContext.create（含 pydantic 等首次导入） | ≈ 0.14-0.16s |
| register_builtin_tools（58 工具） | ≈ 0.084s |
| MainWindow 构建（offscreen） | ≈ 0.135s |

结论：启动没有不必要的重型工作；插件扫描只读 metadata；不预读历史与
Artifact，因此无需引入延迟加载。

## 文件分析（100MB 文件，流式）

| 操作 | 耗时 | 备注 |
| --- | --- | --- |
| Hash（MD5/SHA1/SHA2 六算法单遍） | ≈ 0.52s | ≈ 194 MB/s |
| Strings（min_length=4，ASCII） | ≈ 0.04s | 受 `max_results=20000` 上限提前退出 |
| Entropy（整体） | ≈ 1.86s | 逐字节 Python 循环计数 |
| Hex Viewer | 单页 | 分页读取，只读 256B |

## 网络

| 操作 | 耗时 | 备注 |
| --- | --- | --- |
| TCP Scan 500 个关闭端口（并发 32，超时 1s） | ≈ 16.0s | 本机对 loopback 关闭端口丢弃 SYN，每个探针走满超时 |
| 单端口 TCP Connect（OPEN/CLOSED） | 毫秒级 | 即时拒绝时 |

结论：TCP 扫描吞吐受“关闭端口是否即时拒绝”决定，代码已限制超时与并发；
进度事件在优化前是逐端口上报（500 端口 500 次 UI 更新，大范围会放大）。

## 其他

| 项目 | 数值 |
| --- | --- |
| ToolRegistry 注册 500 工具 + 查询 | < 0.01s |
| 测试套件 | 568 通过 |
| 覆盖率 | core 92%，总体 88% |
| PyInstaller onedir 体积 | ≈ 138MB（含未使用的 Qt QML/PDF 模块与 mypy） |
