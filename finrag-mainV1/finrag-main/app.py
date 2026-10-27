from __future__ import annotations

import hashlib
import hmac

import streamlit as st

from api_client import APISettings, ModelAPIError, load_config
from custom_loader import SUPPORTED_SUFFIXES
from document_processing import BASE_DIR
from rag_pipeline import FinlandTravelRAG, ai_dependencies_available

st.set_page_config(page_title="Finland Travel Assistant", page_icon="🇫🇮", layout="centered")
st.title("🇫🇮 Finland Travel Assistant")
st.caption("Find answers in your travel documents, with sources you can check.")

try:
    secret_values = dict(st.secrets)
except st.errors.StreamlitSecretNotFoundError:
    secret_values = {}
except Exception:
    st.error("Unable to read the app configuration. Ask the administrator to check the Secrets TOML format.")
    st.stop()

config = load_config(BASE_DIR, secret_values)
try:
    api_settings = APISettings.from_mapping(config)
except ModelAPIError as exc:
    st.error(f"Invalid model service configuration: {exc}")
    st.stop()

access_password = config.get("APP_ACCESS_PASSWORD", "")
if access_password:
    password_signature = hashlib.sha256(access_password.encode("utf-8")).hexdigest()
    if st.session_state.get("access_granted") != password_signature:
        with st.form("access_form"):
            entered = st.text_input("Access password", type="password")
            submitted = st.form_submit_button("Open assistant")
        if submitted:
            if hmac.compare_digest(entered.encode("utf-8"), access_password.encode("utf-8")):
                st.session_state.access_granted = password_signature
                st.rerun()
            else:
                st.error("Incorrect access password.")
        st.stop()


def knowledge_signature() -> str:
    digest = hashlib.sha256()
    for path in sorted((BASE_DIR / "data").rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES and not path.name.startswith((".", "~$")):
            digest.update(str(path.relative_to(BASE_DIR)).encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


@st.cache_resource(show_spinner="Loading documents…", max_entries=4)
def init_rag(mode: str, signature: str, settings: APISettings) -> FinlandTravelRAG:
    return FinlandTravelRAG(data_path=BASE_DIR / "data", mode=mode, api_settings=settings)


with st.sidebar:
    st.header("Settings")
    mode_labels = {"Online AI answers": "api", "Document search": "offline"}
    if ai_dependencies_available():
        mode_labels["Local AI answers"] = "ai"
    default_mode = config.get("APP_MODE", "api")
    default_index = next((i for i, value in enumerate(mode_labels.values()) if value == default_mode), 0)
    selected_mode = st.selectbox("Mode", list(mode_labels), index=default_index)
    mode = mode_labels[selected_mode]
    if mode == "offline":
        st.info("Search returns relevant document excerpts. English keywords and common Chinese travel terms are supported. No model download is needed.")
    elif mode == "ai":
        st.caption("Uses local multilingual search and a language model. Models load on first use; answers may take longer on a CPU.")
    else:
        st.caption("Search your travel documents, then let the online model compose an answer.")
        if api_settings.configured:
            st.caption(f"Model: {api_settings.model}")
    if st.button("🔄 Rebuild knowledge base", use_container_width=True):
        init_rag.clear()
        st.session_state.messages = []
        st.success("Cache cleared. Reloading documents.")
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
    st.caption("Add TXT, Markdown, PDF or DOCX files to the data folder, then click Rebuild knowledge base. Scanned PDFs need OCR first.")

try:
    rag = init_rag(mode, knowledge_signature(), api_settings)
except Exception as exc:
    st.error(f"Unable to load the knowledge base: {exc}")
    st.info(f"Check the documents folder: {BASE_DIR / 'data'}")
    st.stop()

with st.sidebar:
    st.metric("Loaded documents", f"{rag.source_count} files")
    st.caption(f"{len(rag.docs)} searchable passages")
    with st.expander("Document loading notes", expanded=bool(rag.warnings)):
        if rag.warnings:
            for warning in rag.warnings:
                st.caption(warning)
        else:
            st.caption("All documents loaded successfully.")

if st.session_state.get("active_mode") != mode:
    st.session_state.messages = []
    st.session_state.active_mode = mode
if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.info("Try asking: When can I see the northern lights? / What can I visit in Helsinki? / What should I pack for summer?")
    st.caption("The included documents are project samples and may be incomplete or inaccurate. Update and verify them before planning a trip.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

api_unavailable = mode == "api" and not api_settings.configured
if api_unavailable:
    st.warning('Online AI answers are not enabled yet. Contact the administrator or select "Document search" in the sidebar.')

if user_input := st.chat_input("Ask a question, e.g. How do I get around Helsinki?", max_chars=1500, disabled=api_unavailable):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        try:
            status_text = {"offline": "Searching documents…", "api": "Preparing an answer from your documents…", "ai": "Loading the local model and preparing an answer…"}
            with st.spinner(status_text[mode]):
                answer = st.write_stream(rag.stream_response(user_input))
        except Exception as exc:
            detail = str(exc) if isinstance(exc, ModelAPIError) or mode != "api" else "The model service is temporarily unavailable. Please try again later."
            answer = f'Unable to answer: {detail}\n\nYou can switch to "Document search" to continue.'
            st.error(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
