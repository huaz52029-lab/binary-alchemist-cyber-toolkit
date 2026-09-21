# Plugin API（插件开发文档）

插件目录：`plugins/<plugin_name>/`，包含 `plugin.json`、入口 Python 文件与可选的
README / tests / resources。

## plugin.json（PluginDefinition）

```json
{
  "id": "binaryalchemist.example",
  "name": "Example Plugin",
  "version": "1.0.0",
  "api_version": "1.0",
  "author": "you",
  "description": "插件描述",
  "entry_point": "plugin.py",
  "enabled": true,
  "permissions": ["filesystem.read"],
  "dependencies": {}
}
```

- `id`：反向域名式命名空间，必须形如 `a.b`。
- `api_version`：当前程序为 `1.0`，兼容 `1.x`（minor ≤ 0）。
- `permissions`：仅声明与展示（filesystem.read/write、network.connect、
  process.read、registry.read、subprocess、admin），本版本不实现沙箱。
- `dependencies`：只检测、不自动安装；缺失时插件标记 FAILED。
- 未知字段被忽略并记录 warning。

## 入口契约

入口文件提供：

```python
def register(context: PluginContext) -> list[BaseTool]:
    return [MyTool()]
```

工具 `ToolDefinition.id` 会被命名空间化为 `<plugin_id>.<tool_id>`，并记录
`plugin_id` 来源；插件不能覆盖官方工具。

## PluginContext

- `logger`：带插件 ID 的统一 Logger。
- `config_manager`：插件自身配置（`data/plugins/<id>.json`）的读写。
- `tool_registry` / `task_manager` / `app_config`：官方公开服务。
- `resource_path(relative)`：解析插件 `resources/` 内路径（禁止越界）。

插件不得访问 MainWindow / Navigation / 核心私有状态；不得创建第二套 Logger、
ToolRegistry 或任务系统；工具页面统一使用 ToolPage。

## 安全说明

插件与主程序同进程运行，拥有与当前用户相同的 Python 执行能力，不属于沙箱。
请只安装可信插件；本版本不提供在线商店、自动下载、自动安装依赖或远程执行。

