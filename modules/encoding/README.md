# Encoding module（编码转换）

Base64 / Base32 / Base58 / Hex / Binary / URL / Unicode / ROT13 / ROT47 /
HTML Entity 十个双向文本转换工具。

- 共享实现：`codecs.py` 提供全部纯函数转换（含人读错误消息），`base.py` 提供
  统一的 `EncodingTool` 执行骨架；每个工具仅声明 ToolDefinition。
- 共享 UI：`ui/encoding_page.py` 的 EncodingToolPage（输入/输出、编码/解码或
  转换按钮、复制、交换、清空、导出）。
- 术语边界：这些工具是编码/格式转换，不是加密。
- Base58 为纯 Python 实现（Bitcoin 字母表），无额外依赖。
- 全部本地执行，不上传任何输入。

