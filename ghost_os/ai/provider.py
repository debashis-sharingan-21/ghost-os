"""Provider abstraction and structured schemas for GHOST.OS forensic AI."""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DiagnosticPrompt(BaseModel):
    """Structured forensic evidence package presented to the AI diagnostic engine."""
    event_id: str
    rule_id: str
    title: str
    severity: str
    ts_onset_ms: int
    ts_recovery_ms: Optional[int] = None
    trigger_evidence: Dict[str, Any]
    summary_stats: Dict[str, Any]
    preceding_samples_count: int
    sample_trace: List[Dict[str, Any]] = Field(default_factory=list)


class Hypothesis(BaseModel):
    rank: int
    title: str
    probability: str  # "HIGH", "MEDIUM", "LOW"
    confidence_pct: int
    reasoning: str


class DiagnosticExplanation(BaseModel):
    """Evidence-grounded structured diagnostic explanation produced by AI."""
    provider: str
    model: str
    event_id: str
    summary: str
    observations: List[str] = Field(default_factory=list)
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    recommended_tests: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    fallback_used: bool = False


class BaseAIProvider:
    """Base interface for AI diagnostic providers."""

    provider_name: str = "base"

    async def is_available(self) -> bool:
        """Checks if the provider runtime is accessible and healthy."""
        raise NotImplementedError

    async def explain_anomaly(self, prompt: DiagnosticPrompt) -> DiagnosticExplanation:
        """Generates a structured forensic diagnostic explanation from evidence."""
        raise NotImplementedError
