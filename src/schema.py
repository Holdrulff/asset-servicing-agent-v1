from __future__ import annotations

from typing import Optional, Literal, Any
from pydantic import BaseModel, Field

Severity = Literal["none", "baixa", "media", "alta"]


class FieldValue(BaseModel):
    value: Optional[str] = None
    confidence_score: float = 0.5
    source_text: Optional[str] = None
    source_location: Optional[str] = None
    rationale: Optional[str] = None


class EventTypeField(FieldValue):
    normalized_code: Optional[str] = None
    classification_evidence: list[str] = Field(default_factory=list)
    title_vs_substance_conflict: bool = False


class ValueOrRatio(BaseModel):
    kind: Literal["cash_per_share", "ratio", "none"] = "none"
    gross_value: Optional[float] = None
    irrf_rate: Optional[float] = None
    net_value: Optional[float] = None
    ratio: Optional[str] = None
    confidence_score: float = 0.5
    source_text: Optional[str] = None
    source_location: Optional[str] = None
    rationale: Optional[str] = None


class DateField(FieldValue):
    pass


class AgentReview(BaseModel):
    required: bool = False
    severity: Severity = "none"
    reasons: list[str] = Field(default_factory=list)


class AgentSubmission(BaseModel):
    issuer: FieldValue
    cnpj: FieldValue
    isin: FieldValue
    ticker: FieldValue
    event_type: EventTypeField
    currency: str = "BRL"
    value_or_ratio: ValueOrRatio
    dates: dict[str, DateField] = Field(default_factory=dict)
    agent_review: AgentReview = Field(default_factory=AgentReview)
    overall_rationale: Optional[str] = None


class IngestionMeta(BaseModel):
    method: Literal["text_native", "ocr"] = "text_native"
    ocr_engine: Optional[str] = None
    pages: Optional[int] = None
    ocr_confidence: Optional[float] = None


class ValidationBlock(BaseModel):
    golden_record: dict[str, Any] = Field(default_factory=dict)
    isin: dict[str, Any] = Field(default_factory=dict)
    coherence: dict[str, Any] = Field(default_factory=dict)


class ConfidenceOverall(BaseModel):
    confidence_score: float = 0.5
    drivers: list[str] = Field(default_factory=list)


class ReviewBlock(BaseModel):
    required: bool = False
    severity: Severity = "none"
    reasons: list[dict[str, Any]] = Field(default_factory=list)
    suggested_action: Optional[str] = None


class AgentAudit(BaseModel):
    steps: int = 0
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    critic_verdict: Optional[dict[str, Any]] = None
    self_consistency_runs: int = 0
    tokens: Optional[int] = None
    duration_s: Optional[float] = None


class ExtractionMetadata(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    timestamp: Optional[str] = None


class Record(BaseModel):
    document_id: str
    source_file: str
    ingestion: IngestionMeta = Field(default_factory=IngestionMeta)
    issuer: FieldValue
    cnpj: FieldValue
    isin: FieldValue
    ticker: FieldValue
    event_type: EventTypeField
    currency: str = "BRL"
    value_or_ratio: ValueOrRatio
    dates: dict[str, DateField] = Field(default_factory=dict)
    validation: ValidationBlock = Field(default_factory=ValidationBlock)
    confidence_overall: ConfidenceOverall = Field(default_factory=ConfidenceOverall)
    review: ReviewBlock = Field(default_factory=ReviewBlock)
    agent_audit: AgentAudit = Field(default_factory=AgentAudit)
    extraction_metadata: ExtractionMetadata = Field(default_factory=ExtractionMetadata)
