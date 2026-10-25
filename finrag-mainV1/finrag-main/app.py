from __future__ import annotations

import hashlib
import hmac

import streamlit as st

from api_client import APISettings, ModelAPIError, load_config
from custom_loader import SUPPORTED_SUFFIXES
from document_processing import BASE_DIR
from rag_pipeline import FinlandTravelRAG, ai_dependencies_available

st.set_page_config(page_title="芬兰旅行资料助手", page_icon="🇫🇮", layout="centered")
st.title("🇫🇮 芬兰旅行资料助手")
st.caption("从你自己的旅行资料中查找内容，并显示来源。")

try:
    secret_values = dict(st.secrets)
except st.errors.StreamlitSecretNotFoundError:
    secret_values = {}
except Exception:
    st.error("应用配置读取失败，请管理员检查 Secrets 的 TOML 格式。")
    st.stop()

config = load_config(BASE_DIR, secret_values)
try:
    api_settings = APISettings.from_mapping(config)
except ModelAPIError as exc:
    st.error(f"模型服务配置有误：{exc}")
    st.stop()

access_password = config.get("APP_ACCESS_PASSWORD", "")
if access_password:
    password_signature = hashlib.sha256(access_password.encode("utf-8")).hexdigest()
    if st.session_state.get("access_granted") != password_signature:
        with st.form("access_form"):
            entered = st.text_input("请输入访问口令", type="password")
            submitted = st.form_submit_button("进入助手")
        if submitted:
            if hmac.compare_digest(entered.encode("utf-8"), access_password.encode("utf-8")):
                st.session_state.access_granted = password_signature
                st.rerun()
            else:
                st.error("访问口令不正确。")
        st.stop()


def knowledge_signature() -> str:
    digest = hashlib.sha256()
    for path in sorted((BASE_DIR / "data").rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES and not path.name.startswith((".", "~$")):
            digest.update(str(path.relative_to(BASE_DIR)).encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


@st.cache_resource(show_spinner="正在读取资料…", max_entries=4)
def init_rag(mode: str, signature: str, settings: APISettings) -> FinlandTravelRAG:
    return FinlandTravelRAG(data_path=BASE_DIR / "data", mode=mode, api_settings=settings)


with st.sidebar:
    st.header("设置")
    mode_labels = {"在线 AI 回答": "api", "本地资料检索": "offline"}
    if ai_dependencies_available():
        mode_labels["本地 AI 回答"] = "ai"
    default_mode = config.get("APP_MODE", "api")
    default_index = next((i for i, value in enumerate(mode_labels.values()) if value == default_mode), 0)
    selected_mode = st.selectbox("工作模式", list(mode_labels), index=default_index)
    mode = mode_labels[selected_mode]
    if mode == "offline":
        st.info("当前直接展示相关原文。支持英文关键词和常见中文旅行词，不需要下载模型。")
    elif mode == "ai":
        st.caption("使用本地多语言检索和中文模型。首次使用需要加载模型，CPU 回答可能需要一些时间。")
    else:
        st.caption("先检索旅行资料，再由在线模型整理回答。")
        if api_settings.configured:
            st.caption(f"回答模型：{api_settings.model}")
    if st.button("🔄 重建知识库", use_container_width=True):
        init_rag.clear()
        st.session_state.messages = []
        st.success("已清除缓存，将重新读取资料。")
    if st.button("清空对话", use_container_width=True):
        st.session_state.messages = []
    st.caption("添加 TXT / Markdown / PDF / DOCX 文件到 data 文件夹后，点击重建知识库。扫描 PDF 需要先做 OCR。")

try:
    rag = init_rag(mode, knowledge_signature(), api_settings)
except Exception as exc:
    st.error(f"知识库加载失败：{exc}")
    st.info(f"请检查资料目录：{BASE_DIR / 'data'}")
    st.stop()

with st.sidebar:
    st.metric("已加载资料", f"{rag.source_count} 个文件 / {len(rag.docs)} 个片段")
    with st.expander("资料读取提示", expanded=bool(rag.warnings)):
        if rag.warnings:
            for warning in rag.warnings:
                st.caption(warning)
        else:
            st.caption("所有资料读取正常。")

if st.session_state.get("active_mode") != mode:
    st.session_state.messages = []
    st.session_state.active_mode = mode
if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.info("可以试试：芬兰什么时候看极光？ / 赫尔辛基有哪些景点？ / 夏天要带什么？")
    st.caption("附带的资料是项目示例，可能不完整或不准确，请自行更新后用于旅行规划。")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

api_unavailable = mode == "api" and not api_settings.configured
if api_unavailable:
    st.warning("在线回答尚未启用。请联系应用管理员，或在侧栏切换到“本地资料检索”。")

if user_input := st.chat_input("输入问题，例如：赫尔辛基的交通", max_chars=1500, disabled=api_unavailable):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        try:
            status_text = {"offline": "正在查找资料…", "api": "正在根据资料生成回答…", "ai": "正在加载本地模型并生成回答…"}
            with st.spinner(status_text[mode]):
                answer = st.write_stream(rag.stream_response(user_input))
        except Exception as exc:
            detail = str(exc) if isinstance(exc, ModelAPIError) or mode != "api" else "模型服务暂时不可用，请稍后重试。"
            answer = f"回答失败：{detail}\n\n可切换到“本地资料检索”继续使用。"
            st.error(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
