from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import BaseModel, Field, HttpUrl, confloat, constr


class PolicySnippet(BaseModel):
    """A single retrieved snippet from a legislative or policy document.

    This model is designed to be RAG-backend agnostic and to provide
    traceability back to the original source (e.g., S.257 PDF).
    """

    text: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Raw text content of the retrieved snippet."
    )
    page: int = Field(
        ...,
        ge=1,
        description="1-based page number within the source document.",
    )
    score: confloat(ge=0.0) = Field(
        ...,
        description=(
            "Similarity score from the vector store. "
            "Lower or higher is backend-dependent but must be comparable within a query."
        ),
    )
    source_path: Path = Field(
        ...,
        description="Filesystem path to the source document (e.g., S.257 PDF).",
    )
    source_title: constr(strip_whitespace=True, min_length=1) = Field(
        ...,
        description="Human-readable title or label for the source document.",
    )


class PolicyQueryResult(BaseModel):
    """Typed result of a policy-aware RAG query over legislative text."""

    query: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Original natural-language query string."
    )
    snippets: List[PolicySnippet] = Field(
        default_factory=list,
        description="Ordered list of the most relevant policy snippets for this query.",
    )


__all__ = ["PolicySnippet", "PolicyQueryResult"]

