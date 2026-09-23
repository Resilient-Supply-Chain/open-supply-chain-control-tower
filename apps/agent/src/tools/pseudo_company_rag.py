from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List, Tuple

import json
import joblib
from pydantic import BaseModel, Field, ValidationError
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class PseudoCompanyRAGConfig(BaseModel):
    """Configuration for the pseudo company supply-chain RAG engine."""

    json_path: Path = Field(
        ...,
        description="Absolute path to the pseudo company supply-chain JSON file.",
    )
    index_dir: Path = Field(
        ...,
        description="Directory where the TF-IDF index will be persisted.",
    )
    source_title: str = Field(
        default="Pseudo Company Supply-Chain Dossier",
        description="Human-readable title for the pseudo dataset.",
    )

    class Config:
        frozen = True
        extra = "forbid"


class PseudoCompanyRAG:
    """Local TF-IDF RAG over a pseudo company supply-chain JSON file."""

    def __init__(self, config: PseudoCompanyRAGConfig) -> None:
        self._config = config
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._records: List[str] = []

    @property
    def config(self) -> PseudoCompanyRAGConfig:
        return self._config

    def _ensure_index_dir(self) -> None:
        self._config.index_dir.mkdir(parents=True, exist_ok=True)

    def _index_exists(self) -> bool:
        return (self._config.index_dir / "pseudo_company_tfidf.joblib").exists()

    def _load_json(self) -> dict[str, Any]:
        try:
            return json.loads(self._config.json_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Pseudo company dataset not found at {self._config.json_path}."
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Pseudo company dataset JSON is invalid.") from exc

    def _iter_records(self, payload: dict[str, Any]) -> Iterable[str]:
        for section, value in payload.items():
            if isinstance(value, list):
                for idx, entry in enumerate(value, start=1):
                    if isinstance(entry, dict):
                        lines = [f"{section} #{idx}"]
                        lines.extend(
                            f"{key}: {val}" for key, val in entry.items()
                        )
                        yield "\n".join(lines)
                    else:
                        yield f"{section} #{idx}: {entry}"
            elif isinstance(value, dict):
                lines = [section]
                lines.extend(f"{key}: {val}" for key, val in value.items())
                yield "\n".join(lines)
            else:
                yield f"{section}: {value}"

    def _build_index(self) -> None:
        payload = self._load_json()
        records = [record.strip() for record in self._iter_records(payload) if record]

        if not records:
            raise RuntimeError("Pseudo company dataset is empty.")

        vectorizer = TfidfVectorizer(
            max_features=25_000,
            ngram_range=(1, 2),
            stop_words="english",
        )
        matrix = vectorizer.fit_transform(records)

        self._ensure_index_dir()
        index_file = self._config.index_dir / "pseudo_company_tfidf.joblib"
        joblib.dump(
            {
                "vectorizer": vectorizer,
                "matrix": matrix,
                "records": records,
            },
            index_file,
        )

        self._vectorizer = vectorizer
        self._matrix = matrix
        self._records = records

    def _load_or_build_index(self) -> None:
        if self._vectorizer is not None and self._matrix is not None:
            return

        self._ensure_index_dir()
        index_file = self._config.index_dir / "pseudo_company_tfidf.joblib"
        if self._index_exists():
            data = joblib.load(index_file)
            self._vectorizer = data["vectorizer"]
            self._matrix = data["matrix"]
            self._records = data["records"]
        else:
            self._build_index()

    def query_supply_chain(
        self, query: str, *, k: int = 3, min_score: float = 0.2
    ) -> List[Tuple[str, float]]:
        try:
            self._load_or_build_index()
        except (FileNotFoundError, ValidationError, ValueError) as exc:
            raise RuntimeError(
                f"Failed to initialize pseudo company RAG index: {exc}"
            ) from exc

        if self._vectorizer is None or self._matrix is None:
            raise RuntimeError("Pseudo company RAG index is not initialized.")

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        top_indices = scores.argsort()[::-1][:k]

        results: List[Tuple[str, float]] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < min_score:
                continue
            results.append((self._records[idx], score))
        return results


__all__ = ["PseudoCompanyRAG", "PseudoCompanyRAGConfig"]
