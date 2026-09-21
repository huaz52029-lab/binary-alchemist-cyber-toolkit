# Example Plugin

验证 Binary Alchemist Plugin API 的示例插件：

- `plugin.json`：清单（id / api_version / permissions / dependencies）。
- `plugin.py`：入口，提供 `register(context) -> list[BaseTool]`。
- 工具 `text.stats` 会被命名空间化为 `binaryalchemist.example.text.stats`，
  并出现在 CTF 分类中。

第三方插件与主程序同进程运行，请只安装可信插件。

