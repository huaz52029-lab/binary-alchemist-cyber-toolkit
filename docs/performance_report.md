# 性能报告（阶段 13）

原则：测量 → 定位 → 优化 → 测试 → 对比。只保留有实测收益且复杂度可接受的
改动；没有为“理论优化”重构稳定代码。

## 实测优化

| 项目 | 优化前 | 优化后 | 改动 |
| --- | --- | --- | --- |
| 文件 Entropy（100MB） | ≈ 1.86s | ≈ 1.53-1.58s | `collections.Counter` 的 C 级字节计数替代逐字节 Python 循环 |
| TCP Scan 进度事件 | 每端口 1 次 UI 更新 | 每 100 端口 1 次 + 最终 100% | 进度节流，65535 端口从 65k 次降到 ~656 次 |
| 打包体积 | ≈ 138MB | ≈ 116MB | 排除 mypy/setuptools 等开发依赖与未使用的 Qt QML/Quick/PDF/VirtualKeyboard |

## 基线复核（优化后，真实运行）

| 项目 | 数值 |
| --- | --- |
| AppContext.create（热） | ≈ 0.003s |
| register_builtin_tools（58） | ≈ 0.054s |
| Hash 100MB（六算法） | ≈ 0.51s（≈ 194 MB/s） |
| Strings 100MB | ≈ 0.04s（2 万结果上限提前退出） |
| Entropy 100MB | ≈ 1.58s |
| TCP Scan 500 关闭端口（并发 32，超时 1s） | ≈ 16.0s（环境受限，见下） |
| Registry 500 注册 + 查询 | < 0.01s |

## 保持不动的部分（测量后判定无需改动）

- **启动延迟加载**：全链路 ≈ 0.4s，无必要引入 lazy import 的复杂度。
- **日志异步化**：日志量小且已轮转，不引入 QueueHandler/QueueListener。
- **TaskManager 调度器**：线程池已限 8 worker，任务结果一次性投递，
  不引入优先级/生产者消费者复杂度。
- **HTTP Client**：每次任务调用创建短期 `httpx.Client` 并随上下文释放，
  已满足“任务生命周期内复用、退出释放”，不引入长期连接池。
- **DNS 缓存**：按规范允许不做，保持现状。
- **进程级 CPU 任务**：MD5/Regex 均在 worker 线程且可取消，未达到需要
  ProcessPoolExecutor 的瓶颈阈值。
- **SQLite 批量插入**：历史由 TaskManager 监听器逐任务写入（实时性优先），
  索引经 `EXPLAIN QUERY PLAN` 验证命中，不重写 Repository。

## 环境相关说明（非缺陷）

本开发机对 127.0.0.1 未监听端口丢弃 SYN，导致“关闭端口”探针走满超时
（TCP Scan 500 端口 ≈ 16s = 500/32 × 1s）。在端口即时拒绝的网络环境中
吞吐会大幅提高。代码层面已保证：每探针超时有界、并发有上限、支持取消与
进度。

## 修复的稳定性问题

- TaskPanel 顶部插入新行后，旧行的索引映射未平移，导致更新错行（已修复并
  加回归测试）。
- 冻结发布的数据目录改为 `%LOCALAPPDATA%\BinaryAlchemist`（保留
  `portable.flag` 便携模式与 `CYBERTOOLKIT_HOME` 覆盖）。
- 新增数据库维护（孤立 Artifact / 断链引用：默认只报告，用户主动清理）与
  ArtifactManager（路径校验、大小统计、受控删除）。

## 结论

启动、文件流式分析、任务调度、SQLite、History/Report 分页均已达到可接受
水平；本次只对三个有实测收益的点做了最小改动，其余按“测量后无需改动”
记录在案。回归与门禁全绿后进入阶段 13 完成状态。
