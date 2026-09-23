from typing import Literal
from pydantic import BaseModel, Field

Tone = Literal["fun", "balanced", "analytical"]


class Fact(BaseModel):
    label: str
    value: float
    unit: str = ""


class VisualPoint(BaseModel):
    label: str
    value: float
    secondary: float | None = None


class Insight(BaseModel):
    id: str
    family: str
    category: str
    section: str = "deep"
    title: str
    description: str
    value: str
    label: str
    participant_ids: list[str] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_total: int = 0
    method: str
    caveat: str | None = None
    visual_type: Literal["bars", "trend", "pair", "none"] = "bars"
    visual: list[VisualPoint] = Field(default_factory=list)
    interpretation: bool = False
    score: float = 0
    source: Literal["measured", "ai"] = "measured"
    moment_kind: str | None = None
    source_quotes: list[dict] = Field(default_factory=list)


class TimelinePeriod(BaseModel):
    period: str
    title: str
    summary: str
    message_count: int
    active_days: int
    late_share: float
    weekend_share: float
    average_length: float
    leader: str | None
    evidence_ids: list[str]
    partial: bool = False


class Report(BaseModel):
    version: str = "2.0"
    conversation_id: str
    title: str
    tone: Tone
    timezone: str
    session_gap_hours: float
    snapshot: dict
    insights: list[Insight]
    timeline: list[TimelinePeriod]
    coverage: dict
    methodology: list[str]
    fingerprint: str
    synthesis: dict | None = None
