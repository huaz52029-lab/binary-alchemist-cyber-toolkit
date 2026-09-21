# CTF module（CTF Workbench）

面向 CTF、安全学习、本地题目分析与授权靶场的**编排层**：组合网络/Web/编码/
密码学/文件/系统模块的既有能力，不重复实现工具。

## 工具

| 工具 | ID | 说明 |
| --- | --- | --- |
| CTF 工作台 | `ctf.workspace` | 本地题目工作区（元数据/附件/结果） |
| Auto Decode | `ctf.auto_decode` | 有界多层候选解码（链/深度/循环检测） |
| Regex 分析器 | `ctf.regex` | 查找/分组/替换 + 常用模板 |
| Flag 提取 | `ctf.flag_tools` | 候选 Flag 提取 + 进一步分析 |
| Text Analysis | `ctf.text_analysis` | 统计/频率/熵（复用熵服务） |
| Crypto Helper | `ctf.crypto_helper` | Hash/XOR/RSA/Base64/Hex 统一入口 |
| 模数计算 | `ctf.mod_math` | mod/powmod/gcd/lcm/inverse |
| 数据转换 | `ctf.data_transform` | 文本/字节/Hex/整数/二进制/Base64 |
| Challenge Analyzer | `ctf.challenge_analyzer` | 候选题型分类 + 工具推荐 |
| CTF Notes | `ctf.notes` | 工作区 Markdown 笔记 |
| CTF Pipeline | `ctf.pipeline` | 本地工具链保存/执行（版本化） |

## 安全边界

- 全部本地：不上传、不联网；附件绝不自动执行；Pipeline 默认拒绝主动网络工具。
- 分类、评分、Flag 候选均为启发式结论，明确标注“候选/非确定性”。
- 日志只记录工具/工作区/任务 ID、输入摘要与耗时，不记录完整 Flag/Token/密文。

