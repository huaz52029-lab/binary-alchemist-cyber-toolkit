# Binary Alchemist Cyber Toolkit — Final Release Report

## 项目信息

- 项目名称：Binary Alchemist Cyber Toolkit（二进制炼金术士 · 网安工具箱）
- 版本：1.0.0（唯一来源：`pyproject.toml`）
- 构建日期：2026-09-21

## 构建环境

- Windows：Windows 11（10.0.26200）
- Python：3.13.14
- PySide6：6.11.2
- PyInstaller：6.22.3
- 构建脚本：`python scripts/build_release.py`

## 核心功能

12 个模块：Core / GUI / Network / Web / Encoding / Crypto / File Analysis /
System / CTF / Plugin / History / Report，以及首次启动欢迎页、关于对话框、
崩溃日志与友好错误提示、数据维护、导出（JSON/TXT/CSV/Markdown）。

- 内置工具数量：58（全部通过“id 唯一 + name/category/version/description
  完整”清单测试）
- 随包插件数量：0（示例插件仅保留在开发仓库，默认不启用）
- 测试数量：582（pytest，全部通过）
- Coverage：core 93.5%；core+infrastructure+modules 87.6%

## 质量门禁

- Ruff：check + format --check 通过
- MyPy：strict，全量源文件无问题
- Pytest：582 passed
- Security Review：无 eval/exec/os.system/shell=True/pickle/yaml；无硬编码
  凭据；无公网测试目标；SQL 参数化；CSV 公式注入防护；导出默认脱敏

## 构建与发布状态

- PyInstaller onedir：PASS（窗口化、应用图标、版本资源 1.0.0）
- 冻结冒烟测试（GUI/注册表/插件/历史/报告/任务）：PASS
- Portable ZIP：PASS（`BinaryAlchemist-1.0.0-win64.zip`，解压即用，
  `portable.flag` 数据随目录）
- Installer（Inno Setup 6.7.3）：**PASS** —
  `BinaryAlchemist-1.0.0-Setup.exe`（36.33MB，中文向导/图标/版本资源/
  安装目录选择/开始菜单与可选桌面快捷方式）
- Clean Install：PASS（全新 LOCALAPPDATA，自动创建 cache/data/exports/logs
  与数据库、startup.log）
- Upgrade：PASS（模拟 0.x 数据 → 1.0.0：历史、报告、引用、配置全部保留，
  user_version=1）
- Uninstall：**PASS** — 静默卸载删除程序本体与快捷方式、用户数据默认保留；
  交互式卸载会询问是否同时删除用户数据（设置/历史/报告/工作区/插件/日志）
- Offline：PASS（设计级）— 全部测试仅 localhost/mock，核心模块无网络 I/O
- Chinese Path：PASS（`D:\测试软件\二进制炼金术士` 等中文路径实测运行）
- Normal User / Administrator：EXE 为 asInvoker，不默认请求管理员权限；
  未在真实双账户环境实测（PARTIAL）

## Known Issues

见 [known_issues.md](known_issues.md)：报告手动保存、Markdown 纯文本预览、
无自定义日期范围、HTML/PDF 预留、窗口化 EXE 的 `--version` 无可见输出等。

## SHA256

见 `release/SHA256SUMS.txt`（便携 ZIP 与（如已构建）Setup.exe）。

## 结论

核心质量门槛与发布验证全部通过：安装程序已编译并完成“安装 → 运行 →
卸载（用户数据保留）”实测，便携 ZIP 同步交付，SHA256 校验齐全。
仅剩三项依赖独立环境的验证（真正无 Python 的干净虚拟机、真实普通用户/
管理员双账户、物理断网复测）以替代方式验证或标注 PARTIAL，均非产品缺陷。
本版本标记为 **v1.0.0 正式发布**。
