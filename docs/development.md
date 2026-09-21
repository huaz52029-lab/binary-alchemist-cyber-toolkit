# 开发指南

## 环境

- Windows 10/11，Python 3.13.x
- PowerShell

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,full]"
```

## 运行

```powershell
python main.py                # 桌面 GUI
python main.py --self-test    # 无界面核心自检
python main.py --smoke-test   # 全栈冒烟（GUI+注册表+插件+历史+报告+任务）
python main.py --plugins      # 启动时加载插件
```

## 质量门禁（提交前必须全绿）

```powershell
python scripts\lint.py          # Ruff check + format
python -m mypy                  # strict 类型检查
python scripts\test.py          # pytest（localhost-only）
python scripts\test.py --cov    # pytest + 覆盖率
python scripts\bench.py         # 性能基准
```

若系统 `python` 不是项目虚拟环境，请改用 `.venv\Scripts\python.exe`。

覆盖率目标：`core` ≥ 90%，`core+infrastructure+modules` ≥ 80%。

## 打包

```powershell
python scripts\build.py           # onedir 构建 + 冻结冒烟测试
python scripts\build.py --clean   # 清理 PyInstaller 缓存
```

产物位于 `dist/BinaryAlchemist/`。规格文件是根目录的
`BinaryAlchemist.spec`；它会过滤环境 PATH 中来源不明的 ICU/OpenSSL/UCRT
DLL，并排除未使用的 Qt 模块与开发工具依赖。

## 新增一个工具

1. 建 `modules/<category>/<tool>/`，写 `BaseTool` 子类。
2. 用 `ToolDefinition` 声明元数据，id 以 `<category>.` 开头。
3. 实现 `run(params, context) -> ToolResult`，绝不阻塞 GUI 线程。
4. 在 `modules/__init__.py` 的 `register_builtin_tools` 中注册。
5. 补 pytest（网络工具只测 localhost/mock）。

导航与工具页由注册表自动生成，不要在 MainWindow 里硬编码按钮。

## 开发插件

```powershell
python scripts\create_plugin.py <name>
```

插件约定见 [plugin_api.md](plugin_api.md)。插件目录结构：

```text
plugins/<plugin-id>/
├── plugin.json   # id / version / api_version / entry_point / dependencies
└── plugin.py     # register(context) -> list[BaseTool]
```

工具 id 会自动加插件命名空间，重复 id 只跳过并报告，不会影响其他插件。
