from __future__ import annotations

from pathlib import Path

from custom_loader import Document, WindowsSafeDirectoryLoader

BASE_DIR = Path(__file__).resolve().parent


def load_and_process_documents(
    data_path: str | Path | None = None,
    chunk_size: int = 900,
    chunk_overlap: int = 120,
    warnings: list[str] | None = None,
) -> list[Document]:
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_size 必须大于 0，且 0 <= chunk_overlap < chunk_size")
    loader = WindowsSafeDirectoryLoader(data_path or BASE_DIR / "data")
    raw_docs = loader.load()
    if warnings is not None:
        warnings.extend(loader.warnings)
    if not raw_docs:
        raise ValueError("没有读到可用资料。请将 TXT、Markdown、PDF 或 DOCX 文件放入 data 目录。")
    chunks: list[Document] = []
    for doc in raw_docs:
        start = 0
        while start < len(doc.page_content):
            end = min(start + chunk_size, len(doc.page_content))
            if end < len(doc.page_content):
                boundary = doc.page_content.rfind("\n", start + chunk_size // 2, end)
                if boundary > start:
                    end = boundary
            content = doc.page_content[start:end].strip()
            if content:
                chunks.append(Document(content, {**doc.metadata, "chunk": len(chunks)}))
            if end == len(doc.page_content):
                break
            start = max(start + 1, end - chunk_overlap)
    return chunks
