# 芬兰旅行资料助手

支持在线模型 API、纯资料检索和可选本地模型三种模式，默认进入在线 API 模式。
云端部署使用轻量依赖，不需要显卡，不下载本地模型权重。

## 本地启动

双击本目录的 `start.bat`，或上一层的 **启动芬兰助手.bat**。
浏览器地址为 http://127.0.0.1:8501 。启动窗口保持打开，按 Ctrl+C 停止。
这是 Streamlit 应用，不通过双击 `app.py` 启动。

本机 Python 为 `D:\py\python.exe`（3.12.10），项目环境位于 `.venv`。
当前虚拟环境复用了电脑已有的基础包；其他电脑首次运行会创建环境并安装依赖。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

## 工作模式

- **在线 AI 回答**：检索本地资料后调用通义千问、DeepSeek 或其他兼容的模型 API。
  需要管理员设置服务地址、模型名及自己的密钥。密钥不在网页中填写或展示。
  未配置密钥时会禁用在线输入，仍可切换资料检索。
- **本地资料检索**：BM25 关键词检索，直接展示相关原文和来源，不生成自然语言回答。
  支持英文及常见中文旅行词映射，不需要联网、密钥或本地模型。
- **本地 AI 回答（可选）**：安装 `requirements-ai.txt` 后出现。
  使用多语言 MiniLM 与 Qwen2.5-0.5B-Instruct。本机已安装并验证中文回答，
  模型缓存位于用户目录的 `.cache/huggingface/hub`。其他电脑首次使用需要下载模型。
  轻量云端部署不安装这组可选依赖。

API 配置、GitHub 上传和 Streamlit Cloud 部署参见 **[DEPLOYMENT.md](DEPLOYMENT.md)**。
本地示例见 `.env.example`；云端 Secrets 示例见 `.streamlit/secrets.toml.example`。
现有 `.env` 已保留，请添加所需变量，不要覆盖原文件，也不要上传真实密钥。

## 更新资料

把 TXT、Markdown、PDF 或 DOCX 放到 `data` 或子文件夹，点击 **重建知识库**。
内容变化也会自动更新缓存。支持 PDF 文本层、Word 段落和表格，扫描 PDF 需先做 OCR。

附带的 `finnish_culture.docx`、`northern_lights_guide.pdf` 实际为纯文本，
加载器已兼容读取。示例资料未经事实核验，不可直接作为可靠旅行建议。

## 测试

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

API 测试使用本机 HTTP 模拟服务，验证请求结构、中文流式回答、来源、错误处理、
缺少密钥和可选访问口令，不产生供应商调用费用。真实 API 联调需要有效密钥。
此前的原代码备份在上一层的 `finrag-original-backup.zip`，不上传 GitHub。
