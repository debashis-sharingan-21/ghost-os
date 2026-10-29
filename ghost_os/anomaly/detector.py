"""Rule-based deterministic anomaly detector for GHOST.OS."""

from __future__ import annotations
import collections
import logging
import time
from typing import List, Dict, Optional, Callable, Any
from ghost_os.protocol.models import TelemetryFrame
from ghost_os.anomaly.rules import (
    AnomalyEvent,
    BaseAnomalyRule,
    FreeFallRule,
    HighGImpactRule,
    HighAngularRateRule,
    SensorFreezeRule,
    SequenceDiscontinuityRule,
    ThermalRunawayRule,
    BrownoutRule,
)
from ghost_os.anomaly.ghost_trace import GhostTraceBuffer

logger = logging.getLogger("ghost_os.anomaly")


class AnomalyDetector:
    """Orchestrates deterministic rule evaluation and Ghost Trace forensic evidence capture."""

    def __init__(
        self,
        trace_buffer: Optional[GhostTraceBuffer] = None,
        on_event: Optional[Callable[[AnomalyEvent], None]] = None,
        window_size: int = 30,
    ) -> None:
        self.trace_buffer = trace_buffer or GhostTraceBuffer(capacity=200)
        self.on_event = on_event
        self.window_size = window_size

        self.sliding_window = collections.deque(maxlen=window_size)
        self.rules: List[BaseAnomalyRule] = [
            FreeFallRule(),
            HighGImpactRule(),
            HighAngularRateRule(),
            SensorFreezeRule(),
            SequenceDiscontinuityRule(),
            ThermalRunawayRule(),
            BrownoutRule(),
        ]

        self.active_events: Dict[str, AnomalyEvent] = {}
        self.resolved_events: collections.deque[AnomalyEvent] = collections.deque(maxlen=100)
        self.total_anomalies_detected: int = 0

    def process_frame(self, frame: TelemetryFrame) -> List[AnomalyEvent]:
        """Processes an incoming telemetry frame. Returns list of newly triggered events."""
        # 1. Update trace and sliding window
        self.trace_buffer.append(frame)
        window_list = list(self.sliding_window)
        self.sliding_window.append(frame)

        newly_triggered: List[AnomalyEvent] = []

        # 2. Check recovery for currently active events
        recovered_rule_ids = []
        for rule_id, event in self.active_events.items():
            rule = next((r for r in self.rules if r.rule_id == rule_id), None)
            if rule and rule.is_cleared(frame):
                event.mark_recovered(frame.ts_ms, frame.seq)
                recovered_rule_ids.append(rule_id)
                self.resolved_events.append(event)
                logger.info(f"Anomaly recovered: {event.title} [Event {event.event_id}]")
                if self.on_event:
                    self.on_event(event)

        for rid in recovered_rule_ids:
            del self.active_events[rid]

        # 3. Evaluate each rule for new breaches
        for rule in self.rules:
            if rule.rule_id in self.active_events:
                # Already active; skip until recovered to avoid duplicate alerts
                continue

            evidence = rule.evaluate(frame, window_list)
            if evidence is not None:
                self.total_anomalies_detected += 1
                event_id = f"EVT-{frame.seq}-{rule.rule_id}"
                preceding_trace = self.trace_buffer.capture_preceding(count=25)

                event = AnomalyEvent(
                    event_id=event_id,
                    rule_id=rule.rule_id,
                    title=rule.title,
                    severity=rule.severity,
                    ts_onset_ms=frame.ts_ms,
                    seq_onset=frame.seq,
                    evidence=evidence,
                    preceding_trace=preceding_trace,
                )
                self.active_events[rule.rule_id] = event
                newly_triggered.append(event)
                logger.warning(f"Anomaly triggered: {rule.title} [Event {event_id}] Severity: {rule.severity}")

                if self.on_event:
                    self.on_event(event)

        return newly_triggered

    @property
    def has_active_anomalies(self) -> bool:
        return len(self.active_events) > 0

    def get_all_events(self) -> List[Dict[str, Any]]:
        """Returns active and recent resolved events combined in reverse chronological order."""
        active = [e.to_dict() for e in self.active_events.values()]
        resolved = [e.to_dict() for e in reversed(self.resolved_events)]
        return active + resolved
