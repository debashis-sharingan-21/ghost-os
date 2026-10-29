"""Tests for AI provider abstraction and deterministic forensic interrogator."""

import pytest
from ghost_os.protocol.models import TelemetryFrame, MPU6050Data
from ghost_os.anomaly.rules import AnomalyEvent
from ghost_os.ai.provider import DiagnosticPrompt
from ghost_os.ai.forensic_provider import ForensicRuleProvider
from ghost_os.ai.interrogator import ForensicInterrogator


@pytest.mark.asyncio
async def test_forensic_rule_provider_free_fall():
    provider = ForensicRuleProvider()
    assert await provider.is_available() is True

    prompt = DiagnosticPrompt(
        event_id="EVT-101-FREE-FALL",
        rule_id="FREE_FALL",
        title="Zero-G Free Fall Excursion",
        severity="CRITICAL",
        ts_onset_ms=100000,
        trigger_evidence={"accel_mag": 0.15, "consecutive_frames": 3},
        summary_stats={"accel_mag_min": 0.15, "accel_mag_max": 9.81},
        preceding_samples_count=20,
    )

    explanation = await provider.explain_anomaly(prompt)
    assert explanation.event_id == "EVT-101-FREE-FALL"
    assert "Free Fall" in explanation.summary or "Zero-G" in explanation.summary
    assert len(explanation.observations) >= 2
    assert len(explanation.hypotheses) >= 1
    assert explanation.hypotheses[0].confidence_pct > 80
    assert len(explanation.recommended_tests) >= 1


@pytest.mark.asyncio
async def test_forensic_interrogator_fallback():
    # Test interrogator with fallback
    interrogator = ForensicInterrogator()
    status = await interrogator.get_active_provider_status()
    assert "fallback_available" in status
    assert status["fallback_available"] is True

    event = AnomalyEvent(
        event_id="EVT-202-IMPACT",
        rule_id="HIGH_G_IMPACT",
        title="Severe Kinetic Impact",
        severity="CRITICAL",
        ts_onset_ms=123000,
        seq_onset=55,
        evidence={"accel_mag": 44.5, "peak_axis_z": 42.0},
    )

    explanation = await interrogator.interrogate_event(event)
    assert explanation.event_id == "EVT-202-IMPACT"
    assert explanation.fallback_used is True  # Ollama is offline, fallback used!
    assert len(explanation.observations) > 0
    assert len(explanation.recommended_tests) > 0
