# Plugins

把插件目录放到这里。每个插件至少包含：

```text
my_plugin/
├── plugin.json   # 必填清单（id/name/version/api_version/entry_point）
├── plugin.py     # 入口：register(context) -> list[BaseTool]
├── README.md     # 可选文档
├── tests/        # 可选测试
└── resources/    # 可选资源（经 PluginContext.resource_path 访问）
```

Example `plugin.json`:

```json
{
  "id": "binaryalchemist.my_plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "api_version": "1.0",
  "author": "you",
  "description": "插件描述",
  "entry_point": "plugin.py",
  "enabled": true,
  "permissions": [],
  "dependencies": {}
}
```

安全说明：插件代码与主程序同进程、同权限运行，不属于沙箱；只安装可信插件。
完整文档见 `docs/plugin_api.md`；开发模板见 `templates/plugin_template/`；
可用 `python scripts/create_plugin.py <name>` 生成骨架。
