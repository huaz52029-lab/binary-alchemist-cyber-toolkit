# File analysis module（文件分析）

完全**静态**的文件分析模块：只读取、解析、展示，绝不执行样本、不加载 DLL、
不运行脚本、不调用在线分析服务、不上传文件或 Hash。

## 工具

| 工具 | ID | 说明 |
| --- | --- | --- |
| 文件信息 | `file_analysis.file_info` | 大小/时间/属性 + Magic Bytes 类型 |
| 文件 Hash | `file_analysis.hashes` | 单次流式 MD5/SHA1/SHA2 |
| 字符串提取 | `file_analysis.strings` | ASCII/UTF-8/UTF-16LE 流式提取 + 线索 |
| 文件熵分析 | `file_analysis.entropy` | Shannon 熵（含 PE Section 级） |
| Hex Viewer | `file_analysis.hex_viewer` | 分页只读 + 偏移跳转 + 搜索 |
| PE 分析 | `file_analysis.pe_analysis` | 头/Section/导入/导出/资源/Overlay |
| IOC 候选提取 | `file_analysis.ioc` | IP/URL/域名/邮箱/路径/注册表候选 |
| 文件安全分析 | `file_analysis.analyzer` | 单文件综合分析 |
| 批量文件分析 | `file_analysis.batch` | 多文件/目录 triage（限数量、可取消） |

## 边界与判定口径

- 高熵、线索关键词、候选 IOC、可执行+可写 Section、Overlay 等只作为
  “事实/启发式”提示，绝不等于恶意判定；第一版不使用 CRITICAL。
- 完整路径仅在 UI 展示，日志只记文件名；所有分析本地完成。
- 大文件全部流式/分块/分页处理；PE 只读取必要结构。

