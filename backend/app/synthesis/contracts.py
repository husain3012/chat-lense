from typing import Literal
from pydantic import BaseModel, Field


class EvidenceQuote(BaseModel):
    message_id: str
    text: str = Field(min_length=1, max_length=600)


class Interpretation(BaseModel):
    family: str = Field(
        description="Specific semantic finding; do not repeat measured candidates"
    )
    title: str = Field(max_length=90)
    description: str = Field(max_length=1600)
    category: str = Field(max_length=80)
    evidence_ids: list[str] = Field(min_length=2, max_length=12)
    fact_ids: list[str] = Field(default_factory=list, max_length=8)
    novelty: float = Field(ge=0, le=10)
    section: Literal["topics", "deep", "turning_points"] = "deep"
    caveat: str = Field(max_length=400)
    moment_kind: Literal[
        "sweet",
        "funny",
        "golden",
        "repair",
        "tension",
        "ritual",
        "connection",
        "romance",
        "intimacy",
        "missing",
        "friendship",
        "deep",
        "ideas",
        "support",
    ] = "connection"
    quotes: list[EvidenceQuote] = Field(default_factory=list, max_length=6)


class SynthesisOutput(BaseModel):
    insights: list[Interpretation] = Field(max_length=20)


class SynthesisRequest(BaseModel):
    tone: Literal["fun", "balanced", "analytical"] = "fun"
    timezone: str = "UTC"
    session_gap: float = Field(default=4, gt=0, le=168)
    consent: bool = False
    refresh: bool = False
