# API 模式与上线

当前发布选择：GitHub 公开仓库；模型服务先使用通义千问，等待管理员配置自己的有效 API 密钥。

## 当前架构

用户浏览器 → Streamlit 应用 → 本地 BM25 资料检索 → 模型 API → 流式显示回答及来源。

API 模式使用关键词检索，中文支持常见旅行关键词映射；它不加载 MiniLM 或 Qwen 权重。
相较原来的多语言向量检索，开放式跨语言查询的召回能力有限，可在后续独立升级检索服务。
模型仅收到用户问题及检索命中的资料片段；API 密钥始终由后端读取。
默认单次回答上限为 512 tokens，连接超时 10 秒、读取超时 60 秒，不自动重试付费请求。

## 本地配置

现有 `.env` 请保留，只添加以下变量；不要将模板直接覆盖现有文件：

```dotenv
APP_MODE=api
LLM_PROVIDER=qwen
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
LLM_API_KEY=填入你自己的密钥
```

重启或刷新应用。通义千问的密钥在[阿里云百炼控制台](https://bailian.console.aliyun.com/)创建。
北京地域的密钥需匹配北京接口；其他地域请使用对应的 Base URL。
阿里云也支持业务空间专属域名，以自己控制台提供的地址为准。
参考[官方接入说明](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)。
默认 `qwen-plus` 是托管模型服务的名称，不等同于之前本机运行的 Qwen2.5-0.5B。
如果需要托管的开源模型，请在供应商控制台选择可用模型，并修改 `LLM_MODEL`，无需改代码。

DeepSeek 配置示例（同时替换 provider、base URL、model，防止混用接口与密钥）：

```dotenv
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash
LLM_API_KEY=填入你自己的密钥
```

还支持 `LLM_PROVIDER=custom`，此时必须自行设置服务地址、模型名及密钥。
兼容服务使用 `/chat/completions` 和 SSE 流式协议。Base URL 不应包含 `/chat/completions`。
配置优先级：进程环境变量 > Streamlit Secrets > 本地 `.env` > 默认值。
`DASHSCOPE_API_KEY`、`DEEPSEEK_API_KEY` 可分别作为对应供应商的密钥别名。

## GitHub 与 Streamlit Cloud

GitHub 保存代码；Streamlit Cloud 运行 Python 并提供访问网址。GitHub Pages 不运行此后端。
本项目选择公开仓库；Streamlit 需要获得仓库访问权限。真实密钥仍只在部署平台 Secrets 中配置。

部署参数：

| 项目 | 值 |
| --- | --- |
| Main file path | `finrag-mainV1/finrag-main/app.py` |
| Python | `3.12` |
| Dependencies | 应用目录内的 `requirements.txt` |
| Secrets | 复制 `.streamlit/secrets.toml.example` 并填入真实值 |

不要安装 `requirements-ai.txt` 或 `requirements-tested.txt` 到这个轻量部署。
`.env`、`.streamlit/secrets.toml`、`.venv`、模型和日志都不上传 GitHub。
云端仅安装基础依赖，因此不会提供本地模型模式；没有配置 API 密钥时仍可使用资料检索。

更新公开资料：修改 `data` 中的文件并推送 GitHub，应用更新后会通过内容摘要自动重建缓存。
附带的示例 `.pdf`、`.docx` 实际为文本，加载器已兼容。

## 小范围试用

在部署平台 Secrets 设置 `APP_ACCESS_PASSWORD` 可启用共享访问口令。它适合邀请少量测试者，
不等同于独立用户账号、完整限流或计费系统。留空时无需口令。
模型 API 的调用费用由密钥所属账户承担，预算和额度请在供应商控制台管理。
公开规模使用前还需依据实际访问量增加身份管理、限流及持久化存储。

## 验证与当前状态

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

自动测试使用本机模拟 HTTP 服务验证真实请求结构、中文流式输出、错误提示和连接关闭，
无需 API 密钥且不会产生模型费用。真实供应商联调需要你的有效 API 密钥。
GitHub 上传完成以实际仓库链接为准；上线完成以能正常访问的 Streamlit 网址为准。
