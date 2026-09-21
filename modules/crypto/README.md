# Cryptography module（密码学）

- Hash 计算器（`crypto.hash`）：文本/文件 MD5-SHA512，分块读取，大小写不敏感对比。
- MD5 哈希逆向分析器（`crypto.md5_reverse`）：候选验证/字典/有限暴力（离线）。
- XOR 工具（`crypto.xor`）：单字节、遍历评分、重复密钥、等长 Hex XOR。
- JWT 解析器（`crypto.jwt`）：离线结构解析与声明分析，不猜测密钥、不攻击。
- RSA 辅助（`crypto.rsa_helper`）：参数数学关系与 PEM 公钥解析。

所有工具离线运行；日志不记录完整 Token、私钥或文件路径；启发式结论（如 XOR
评分、Auto Decode 候选）都显式标注为非确定性参考。

