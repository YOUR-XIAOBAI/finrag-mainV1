# FinRAG 芬兰旅行资料助手

基于 Streamlit 的旅行资料问答应用：本地检索资料，再调用模型 API 生成回答并显示来源。
默认云端部署不安装 PyTorch，不下载本地大模型。保留纯资料检索模式和可选本地模型模式。

应用代码：[finrag-mainV1/finrag-main](finrag-mainV1/finrag-main)。

在线回答先接入通义千问。真实 API 密钥仅在本地
环境变量或部署平台 Secrets 配置，公开源码不包含密钥。

## 在 Streamlit Community Cloud 部署

1. 将本仓库上传 GitHub，并登录 https://share.streamlit.io 。
2. 创建应用，选择本仓库以及实际推送的分支。
3. **Main file path** 填写 `finrag-mainV1/finrag-main/app.py`。
4. **Advanced settings** 选择 Python **3.12**。
5. 把应用目录下 `.streamlit/secrets.toml.example` 的内容复制到 **Secrets**，填写自己的模型 API 密钥。
6. 点击 Deploy，等安装完成后使用平台分配的 `https://….streamlit.app` 地址。

详细配置：[部署说明](finrag-mainV1/finrag-main/DEPLOYMENT.md)。

本仓库不包含真实 API 密钥、虚拟环境、模型权重、日志或原始备份压缩包。
附带的旅行资料为开发示例，未核验其内容和时效性；用于真实旅行规划前应更新。
