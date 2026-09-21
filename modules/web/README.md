# Web security module（Web 安全）

面向 Web 安全学习、站点配置检查、靶场、CTF 与授权测试的 HTTP/HTTPS 分析模块。

## 工具

| 工具 | ID | 说明 |
| --- | --- | --- |
| URL 解析器 | `web.url_parser` | URL 结构与查询参数分解 |
| HTTP Header 分析器 | `web.http_headers` | HEAD（必要时回退 GET）+ 响应头 |
| Cookie 安全分析 | `web.cookie_analysis` | Set-Cookie 属性（值默认脱敏） |
| Web 安全 Header 检查 | `web.security_headers` | 9 项安全响应头存在性检查 |
| TLS 信息分析 | `web.tls_info` | 版本/密码套件/证书/验证 |
| HTTP 请求分析 | `web.http_analysis` | 综合：请求、响应、重定向、安全头、Cookie、TLS、页面元信息 |

## 安全边界

- 仅 GET/HEAD；仅 http/https；统一 UA `BinaryAlchemist-CyberToolkit/<version>`。
- 所有请求有超时、有界响应体、最大重定向数；TLS 默认校验、绝不绕过。
- Authorization/Cookie 等敏感 Header 默认脱敏；Cookie 值不写日志；不记录
 完整 Token 或私钥；全部本地处理、不上传任何数据。
- 缺少安全 Header、Cookie 属性缺失、自签名证书等都按“事实”报告，谨慎定级，
  不宣称“存在漏洞”；不实现任何漏洞利用、爆破或隐蔽扫描能力。

## 测试

`tests/web/` 全部离线确定性：本地 HTTP 服务器（200/301/302/404/500/慢速/大响应/
安全头/Cookie/HTML）与本地 TLS 服务器（自签名证书），无公网依赖。

