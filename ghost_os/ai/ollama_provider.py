"""Local open-weight LLM provider using Ollama HTTP API."""

from __future__ import annotations
import json
import logging
import time
from typing import Optional
import httpx
from ghost_os.ai.provider import (
    BaseAIProvider,
    DiagnosticPrompt,
    DiagnosticExplanation,
    Hypothesis,
)

logger = logging.getLogger("ghost_os.ai.ollama")


class OllamaProvider(BaseAIProvider):
    """Integrates with locally running Ollama instance."""

    provider_name = "Ollama"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "llama3.2:1b",
        timeout_sec: float = 8.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout_sec

    async def is_available(self) -> bool:
        """Pings Ollama API to verify connectivity."""
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def explain_anomaly(self, prompt: DiagnosticPrompt) -> DiagnosticExplanation:
        start_t = time.time()
        system_prompt = (
            "You are GHOST.OS AI Forensics Engineer. Analyze this telemetry anomaly evidence.\n"
            "You must return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "summary": "Short technical summary",\n'
            '  "observations": ["Observed factual metrics"],\n'
            '  "hypotheses": [{"rank": 1, "title": "Physical cause", "probability": "HIGH", "confidence_pct": 90, "reasoning": "Physics reasoning"}],\n'
            '  "uncertainties": ["Factors not measurable from sensor data"],\n'
            '  "recommended_tests": ["Hardware engineering bench tests to verify or repair"]\n'
            "}\n"
            "Never recommend autonomous execution of shell commands, firmware flashing, or GPIO actuation."
        )

        user_content = (
            f"EVENT ID: {prompt.event_id}\n"
            f"FAULT TITLE: {prompt.title}\n"
            f"SEVERITY: {prompt.severity}\n"
            f"TRIGGER EVIDENCE: {json.dumps(prompt.trigger_evidence)}\n"
            f"TRACE STATS: {json.dumps(prompt.summary_stats)}\n"
        )

        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\nEvidence:\n{user_content}",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data.get("response", "{}")

            parsed = json.loads(raw_text)
            hypotheses = []
            for h in parsed.get("hypotheses", []):
                hypotheses.append(
                    Hypothesis(
                        rank=h.get("rank", 1),
                        title=h.get("title", "Unknown"),
                        probability=h.get("probability", "MEDIUM"),
                        confidence_pct=int(h.get("confidence_pct", 50)),
                        reasoning=h.get("reasoning", ""),
                    )
                )

            latency = (time.time() - start_t) * 1000
            return DiagnosticExplanation(
                provider=self.provider_name,
                model=self.model,
                event_id=prompt.event_id,
                summary=parsed.get("summary", prompt.title),
                observations=parsed.get("observations", []),
                hypotheses=hypotheses,
                uncertainties=parsed.get("uncertainties", []),
                recommended_tests=parsed.get("recommended_tests", []),
                latency_ms=round(latency, 2),
                fallback_used=False,
            )
