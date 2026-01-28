from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import joblib
from pydantic import BaseModel, Field, ValidationError
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.tools.schema import PolicyQueryResult, PolicySnippet
from src.tools.pdf_parser import parse_legislation_text
from config.settings import RagMode


class LegislationRAGConfig(BaseModel):
    """Configuration for the LegislationRAG engine.

    This class encapsulates all filesystem paths and model configuration
    necessary for deterministic, local RAG over legislative materials.
    """

    pdf_path: Path = Field(
        ...,
        description="Absolute path to the S.257 legislative PDF file.",
    )
    index_dir: Path = Field(
        ...,
        description="Directory where the FAISS vector store will be persisted.",
    )
    source_title: str = Field(
        default="S.257 – Promoting Resilient Supply Chains Act of 2025",
        description="Human-readable title for the source legislation.",
    )
    rag_mode: RagMode = Field(
        default="LEGACY",
        description="RAG parsing mode: LEGACY (local) or ADVANCED (LlamaParse).",
    )
    markdown_cache_path: Optional[Path] = Field(
        default=None,
        description="Optional cached Markdown path for ADVANCED parsing.",
    )
    llama_cloud_api_key: Optional[str] = Field(
        default=None,
        description="API key for LlamaParse when ADVANCED mode is enabled.",
    )
    class Config:
        frozen = True
        extra = "forbid"


class LegislationRAG:
    """RAG engine for querying S.257 legislative text using a local TF-IDF index.

    Responsibilities:
    - Load the S.257 PDF from disk.
    - Split the document into overlapping text chunks.
    - Build or load a FAISS vector store persisted under `.vector_store/`.
    - Provide a high-level `query_policy()` method that returns typed,
      traceable snippets including page numbers and source metadata.
    """

    def __init__(self, config: LegislationRAGConfig) -> None:
        self._config = config
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._matrix = None
        self._snippets_meta: List[Tuple[str, int]] = []  # (text, page)

    @property
    def config(self) -> LegislationRAGConfig:
        """Return immutable configuration used by this RAG engine.

        Returns:
            The immutable `LegislationRAGConfig` instance.
        """

        return self._config

    def _ensure_index_dir(self) -> None:
        """Ensure the parent directory for the TF-IDF index exists."""

        self._config.index_dir.mkdir(parents=True, exist_ok=True)

    def _index_exists(self) -> bool:
        """Check whether a TF-IDF index has already been persisted on disk."""

        index_file = self._config.index_dir / "s257_tfidf.joblib"
        return index_file.exists()

    def _build_index(self) -> None:
        """Build a TF-IDF vector index from the S.257 PDF.

        This method is idempotent: if the index already exists, the caller
        should avoid invoking it directly and call `_load_or_build_index()`
        instead.
        """

        snippets = parse_legislation_text(
            pdf_path=self._config.pdf_path,
            rag_mode=self._config.rag_mode,
            cache_path=self._config.markdown_cache_path,
            api_key=self._config.llama_cloud_api_key,
        )

        texts: List[str] = []
        meta: List[Tuple[str, int]] = []

        for text, locator in snippets:
            cleaned = text.strip()
            if not cleaned:
                continue
            texts.append(cleaned)
            meta.append((cleaned, locator))

        if not texts:
            raise RuntimeError("No text could be extracted from the S.257 PDF.")

        vectorizer = TfidfVectorizer(
            max_features=50_000,
            ngram_range=(1, 2),
            stop_words="english",
        )
        matrix = vectorizer.fit_transform(texts)

        self._ensure_index_dir()
        index_file = self._config.index_dir / "s257_tfidf.joblib"
        joblib.dump(
            {
                "vectorizer": vectorizer,
                "matrix": matrix,
                "meta": meta,
            },
            index_file,
        )

        self._vectorizer = vectorizer
        self._matrix = matrix
        self._snippets_meta = meta

    def _load_or_build_index(self) -> None:
        """Load an existing TF-IDF index or build it if missing."""

        if self._vectorizer is not None and self._matrix is not None:
            return

        self._ensure_index_dir()
        index_file = self._config.index_dir / "s257_tfidf.joblib"
        if self._index_exists():
            data = joblib.load(index_file)
            self._vectorizer = data["vectorizer"]
            self._matrix = data["matrix"]
            self._snippets_meta = data["meta"]
        else:
            self._build_index()

    def query_policy(
        self, query: str, *, k: int = 4
    ) -> PolicyQueryResult:
        """Query the S.257 vector index for relevant policy snippets.

        Args:
            query: Natural-language question about legislative or policy context.
            k: Maximum number of snippets to return.

        Returns:
            A `PolicyQueryResult` containing ordered snippets with scores and metadata.
        """

        try:
            self._load_or_build_index()
        except (FileNotFoundError, ValidationError, ValueError) as exc:
            raise RuntimeError(f"Failed to initialize legislative RAG index: {exc}") from exc

        if self._vectorizer is None or self._matrix is None:
            raise RuntimeError("Legislation RAG index is not initialized.")

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]

        # Get indices of top-k scores
        top_indices = scores.argsort()[::-1][:k]

        snippets: list[PolicySnippet] = []
        for idx in top_indices:
            text, page_num = self._snippets_meta[idx]
            snippets.append(
                PolicySnippet(
                    text=text,
                    page=int(page_num),
                    score=float(scores[idx]),
                    source_path=self._config.pdf_path,
                    source_title=self._config.source_title,
                )
            )

        return PolicyQueryResult(query=query, snippets=snippets)


__all__ = ["LegislationRAG", "LegislationRAGConfig"]

