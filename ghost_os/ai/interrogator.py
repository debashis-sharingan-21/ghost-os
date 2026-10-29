"""Forensic Interrogator coordinating primary and fallback AI providers."""

from __future__ import annotations
import logging
from typing import Dict, Optional, Any
from ghost_os.anomaly.rules import AnomalyEvent
from ghost_os.ai.provider import (
    BaseAIProvider,
    DiagnosticPrompt,
    DiagnosticExplanation,
)
from ghost_os.ai.ollama_provider import OllamaProvider
from ghost_os.ai.forensic_provider import ForensicRuleProvider

logger = logging.getLogger("ghost_os.ai.interrogator")


class ForensicInterrogator:
    """Coordinates local AI diagnostic interrogation with zero-crash fallback guarantees."""

    def __init__(
        self,
        primary_provider: Optional[BaseAIProvider] = None,
        fallback_provider: Optional[BaseAIProvider] = None,
    ) -> None:
        self.primary = primary_provider or OllamaProvider()
        self.fallback = fallback_provider or ForensicRuleProvider()
        self.cached_explanations: Dict[str, DiagnosticExplanation] = {}

    async def get_active_provider_status(self) -> Dict[str, Any]:
        """Returns the operational status of available AI runtimes."""
        ollama_ok = await self.primary.is_available()
        return {
            "primary_available": ollama_ok,
            "primary_provider": self.primary.provider_name,
            "fallback_available": True,
            "fallback_provider": self.fallback.provider_name,
            "active_mode": "Ollama LLM" if ollama_ok else "Deterministic Forensic Engine (Offline Fallback)",
        }

    async def interrogate_event(
        self,
        event: AnomalyEvent,
        trace_summary: Optional[Dict[str, Any]] = None,
    ) -> DiagnosticExplanation:
        """Generates evidence-grounded diagnosis for an anomaly event."""
        if event.event_id in self.cached_explanations:
            return self.cached_explanations[event.event_id]

        prompt = DiagnosticPrompt(
            event_id=event.event_id,
            rule_id=event.rule_id,
            title=event.title,
            severity=event.severity,
            ts_onset_ms=event.ts_onset_ms,
            ts_recovery_ms=event.ts_recovery_ms,
            trigger_evidence=event.evidence,
            summary_stats=trace_summary or {},
            preceding_samples_count=len(event.preceding_trace),
            sample_trace=event.preceding_trace[-10:] if event.preceding_trace else [],
        )

        # Try primary provider if available
        explanation: Optional[DiagnosticExplanation] = None
        if await self.primary.is_available():
            try:
                explanation = await self.primary.explain_anomaly(prompt)
                logger.info(f"Generated explanation via {self.primary.provider_name} for {event.event_id}")
            except Exception as e:
                logger.warning(f"Primary provider {self.primary.provider_name} failed: {e}. Falling back...")

        # Fallback if primary unavailable or failed
        if explanation is None:
            explanation = await self.fallback.explain_anomaly(prompt)
            explanation.fallback_used = True
            logger.info(f"Generated explanation via fallback {self.fallback.provider_name} for {event.event_id}")

        self.cached_explanations[event.event_id] = explanation
        return explanation
