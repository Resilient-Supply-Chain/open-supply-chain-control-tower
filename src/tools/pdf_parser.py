from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from pypdf import PdfReader

from config.settings import RagMode


def _clean_markdown_text(markdown_text: str) -> str:
    """Normalize Markdown extracted from LlamaParse for retrieval."""

    text = markdown_text.replace("\r\n", "\n")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"^[ \t]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(
        line
        for line in text.splitlines()
        if not re.match(r"^\s*(?:page\s+)?\d+\s*$", line, flags=re.IGNORECASE)
    )
    return text.strip()


def _chunk_markdown(markdown_text: str, *, max_chars: int = 1500, overlap: int = 200) -> List[str]:
    """Split Markdown into retrieval chunks while keeping section context."""

    paragraphs = [p.strip() for p in markdown_text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for paragraph in paragraphs:
        para_len = len(paragraph)
        if current and current_len + para_len + 2 > max_chars:
            chunk = "\n\n".join(current).strip()
            if chunk:
                chunks.append(chunk)
            if overlap > 0 and chunk:
                overlap_text = chunk[-overlap:]
                current = [overlap_text]
                current_len = len(overlap_text)
            else:
                current = []
                current_len = 0

        current.append(paragraph)
        current_len += para_len + 2

    if current:
        chunk = "\n\n".join(current).strip()
        if chunk:
            chunks.append(chunk)

    return chunks


def parse_pdf_legacy(pdf_path: Path) -> List[Tuple[str, int]]:
    """Extract page-level text from a PDF using the local parser.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        A list of (text, page_number) tuples.
    """

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at {pdf_path}")

    reader = PdfReader(str(pdf_path))
    texts: List[Tuple[str, int]] = []

    for page_index, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                f"Failed to extract text from page {page_index + 1}: {exc}"
            ) from exc

        page_text = page_text.strip()
        if not page_text:
            continue

        texts.append((page_text, page_index + 1))

    if not texts:
        raise RuntimeError("No text could be extracted from the PDF.")

    return texts


def parse_pdf_advanced(
    pdf_path: Path, *, cache_path: Path, api_key: str
) -> List[Tuple[str, int]]:
    """Parse PDF with LlamaParse and return chunked Markdown text.

    Args:
        pdf_path: Path to the PDF file.
        cache_path: Path to a cached Markdown file.
        api_key: LlamaParse API key.

    Returns:
        A list of (chunk_text, chunk_index) tuples.
    """

    if cache_path.exists():
        markdown_text = cache_path.read_text(encoding="utf-8")
    else:
        from llama_parse import LlamaParse

        parser = LlamaParse(api_key=api_key, result_type="markdown")
        documents = parser.load_data(str(pdf_path))
        markdown_text = "\n\n".join(doc.text for doc in documents if doc.text)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(markdown_text, encoding="utf-8")

    cleaned = _clean_markdown_text(markdown_text)
    chunks = _chunk_markdown(cleaned)
    return [(chunk, idx + 1) for idx, chunk in enumerate(chunks)]


def parse_legislation_text(
    *, pdf_path: Path, rag_mode: RagMode, cache_path: Path | None, api_key: str | None
) -> List[Tuple[str, int]]:
    """Route parsing based on RAG mode and return text snippets.

    Args:
        pdf_path: Path to the PDF file.
        rag_mode: Parsing mode, either "LEGACY" or "ADVANCED".
        cache_path: Optional cached Markdown file path.
        api_key: Optional LlamaParse API key.

    Returns:
        A list of (text, locator) tuples.
    """

    if rag_mode == "ADVANCED":
        if not api_key:
            raise ValueError("LLAMA_CLOUD_API_KEY is required for ADVANCED mode.")
        if cache_path is None:
            raise ValueError("cache_path is required for ADVANCED mode.")
        return parse_pdf_advanced(pdf_path, cache_path=cache_path, api_key=api_key)

    return parse_pdf_legacy(pdf_path)


__all__ = ["parse_legislation_text"]
