"""Shared extraction shape, initially used to validate curated reference data.

These models validate structure/types only. Source evidence and numeric scoring
belong to the deterministic evaluator in Module 05.
"""

from pydantic import BaseModel, ConfigDict


class SettlementEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    estimated: str | None
    allowable: str | None


class SettlementExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    estimated_settlement_mm: float | None
    allowable_settlement_mm: float | None
    evidence: SettlementEvidence
