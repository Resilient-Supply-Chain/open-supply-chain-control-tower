from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, constr

from .signal import AlertPriority, RiskSignal


class AffectedSME(BaseModel):
    """Minimal representation of a potentially affected SME."""

    sme_id: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Stable identifier for the SME in the local registry.",
    )
    name: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Legal or common name of the SME.",
    )
    county: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="County or equivalent sub-national unit.",
    )
    sector: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Simple sector label (e.g., agriculture, logistics).",
    )


class ResilienceReport(BaseModel):
    """Structured representation of a generated resilience / alert report."""

    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the report was generated.",
    )
    priority: AlertPriority = Field(
        ..., description="Derived alert priority for the risk signal.",
    )
    risk_signal: RiskSignal = Field(
        ..., description="The original validated risk signal driving this report.",
    )
    affected_smes: List[AffectedSME] = Field(
        default_factory=list,
        description="List of SMEs potentially affected within the target geography.",
    )
    markdown_alert: constr(strip_whitespace=True, min_length=1) = Field(
        ..., description="Markdown-formatted supply chain alert.",
    )
    notes: Optional[constr(strip_whitespace=True, min_length=1)] = Field(
        default=None,
        description="Optional internal notes or caveats (e.g., data quality, assumptions).",
    )


__all__ = ["AffectedSME", "ResilienceReport"]

