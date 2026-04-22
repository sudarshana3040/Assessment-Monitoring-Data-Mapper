"""
Assessment Monitoring Data Mapper
==================================
Converts raw proctoring events into structured JSON outputs
with risk scoring, classification, and flagging logic.

Usage:
    mapper = AssessmentDataMapper(candidate_id="C001", session_id="S123", question_id="Q5")
    mapper.record_event("PHONE", confidence=0.92)
    mapper.record_event("LOOKING_AWAY", confidence=0.75)
    output = mapper.generate_report()
    print(json.dumps(output, indent=2))
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────
# 1. RISK MAPPING CONFIGURATION
# ─────────────────────────────────────────────

EVENT_RISK_MAP = {
    # Event Type       : { score, severity, category }
    "PHONE":             {"score": 60,  "severity": "HIGH",   "category": "device_usage"},
    "MULTIPLE_PERSONS":  {"score": 55,  "severity": "HIGH",   "category": "environment"},
    "NO_FACE":           {"score": 30,  "severity": "MEDIUM", "category": "presence"},
    "LOOKING_AWAY":      {"score": 15,  "severity": "LOW",    "category": "attention"},
    "BAD_POSTURE":       {"score": 10,  "severity": "LOW",    "category": "posture"},
    "UNKNOWN":           {"score": 5,   "severity": "LOW",    "category": "unclassified"},
}

# Risk classification thresholds (final accumulated score)
RISK_THRESHOLDS = {
    "LOW":    (0,  39),
    "MEDIUM": (40, 69),
    "HIGH":   (70, 100),
}

# Flags are raised when an event's severity meets or exceeds this level
FLAG_SEVERITY_THRESHOLD = {"HIGH", "MEDIUM"}


# ─────────────────────────────────────────────
# 2. RISK SCORING ENGINE
# ─────────────────────────────────────────────

class RiskScoringEngine:
    """
    Accumulates risk scores from proctoring events.
    Applies confidence weighting and caps at 100.
    """

    def __init__(self):
        self._score: float = 0.0

    @property
    def score(self) -> int:
        return min(100, int(round(self._score)))

    def add_event(self, event_type: str, confidence: float) -> int:
        """
        Adds weighted risk from an event.
        Score contribution = base_score × confidence (0.0–1.0).
        """
        config = EVENT_RISK_MAP.get(event_type, EVENT_RISK_MAP["UNKNOWN"])
        weighted = config["score"] * max(0.0, min(1.0, confidence))
        self._score = min(100.0, self._score + weighted)
        return self.score

    def classify(self) -> str:
        """Returns LOW / MEDIUM / HIGH based on accumulated score."""
        s = self.score
        for level, (lo, hi) in RISK_THRESHOLDS.items():
            if lo <= s <= hi:
                return level
        return "HIGH"

    def reset(self):
        self._score = 0.0


# ─────────────────────────────────────────────
# 3. EVENT LOG ENTRY
# ─────────────────────────────────────────────

class EventLogEntry:
    """
    Represents one proctoring event with full metadata.
    """

    def __init__(
        self,
        event_type: str,
        confidence: float,
        candidate_id: Optional[str] = None,
        session_id: Optional[str] = None,
        question_id: Optional[str] = None,
        frame_index: Optional[int] = None,
        extra_metadata: Optional[dict] = None,
    ):
        config = EVENT_RISK_MAP.get(event_type, EVENT_RISK_MAP["UNKNOWN"])

        self.event_id     = str(uuid.uuid4())
        self.timestamp    = datetime.now(timezone.utc).isoformat()
        self.event_type   = event_type
        self.confidence   = round(max(0.0, min(1.0, confidence)), 4)
        self.severity     = config["severity"]
        self.category     = config["category"]
        self.base_score   = config["score"]
        self.weighted_score = round(config["score"] * self.confidence, 2)

        # Tracking identifiers
        self.candidate_id = candidate_id
        self.session_id   = session_id
        self.question_id  = question_id
        self.frame_index  = frame_index
        self.extra_metadata = extra_metadata or {}

    def to_dict(self) -> dict:
        return {
            "event_id":       self.event_id,
            "timestamp":      self.timestamp,
            "candidate_id":   self.candidate_id,
            "session_id":     self.session_id,
            "question_id":    self.question_id,
            "frame_index":    self.frame_index,
            "log": {
                "event":          self.event_type,
                "category":       self.category,
                "severity":       self.severity,
                "confidence":     self.confidence,
                "base_score":     self.base_score,
                "weighted_score": self.weighted_score,
            },
            "metadata": self.extra_metadata,
        }


# ─────────────────────────────────────────────
# 4. ASSESSMENT DATA MAPPER  (main class)
# ─────────────────────────────────────────────

class AssessmentDataMapper:
    """
    Core mapper: collects events during a proctoring session,
    scores them, and emits structured JSON for backend storage
    and admin review.

    Parameters
    ----------
    candidate_id : str   – Unique ID of the candidate
    session_id   : str   – Assessment session ID
    question_id  : str   – Current question being answered (optional)
    """

    def __init__(
        self,
        candidate_id: str = "UNKNOWN",
        session_id:   str = "UNKNOWN",
        question_id:  str = "UNKNOWN",
    ):
        self.candidate_id = candidate_id
        self.session_id   = session_id
        self.question_id  = question_id

        self._engine   = RiskScoringEngine()
        self._events:  list[EventLogEntry] = []
        self._flags:   list[str] = []
        self._frame_counter = 0
        self._session_start = datetime.now(timezone.utc).isoformat()

    # ── Public API ────────────────────────────

    def record_event(
        self,
        event_type:     str,
        confidence:     float = 1.0,
        extra_metadata: Optional[dict] = None,
    ) -> dict:
        """
        Record a proctoring event and return its structured output.
        Call this every time the CV pipeline detects a violation.
        """
        self._frame_counter += 1

        entry = EventLogEntry(
            event_type=event_type,
            confidence=confidence,
            candidate_id=self.candidate_id,
            session_id=self.session_id,
            question_id=self.question_id,
            frame_index=self._frame_counter,
            extra_metadata=extra_metadata,
        )
        self._events.append(entry)

        # Score accumulation
        current_score = self._engine.add_event(event_type, confidence)

        # Flagging logic
        if entry.severity in FLAG_SEVERITY_THRESHOLD:
            if event_type not in self._flags:
                self._flags.append(event_type)

        # Build per-event structured output
        output = entry.to_dict()
        output["risk_analysis"] = {
            "risk_score":  current_score,
            "risk_level":  self._engine.classify(),
            "flags":       list(self._flags),
        }

        return output

    def update_question(self, question_id: str):
        """Call when the candidate moves to a new question."""
        self.question_id = question_id

    def generate_report(self) -> dict:
        """
        Generate a full session report after monitoring ends.
        Suitable for backend storage and admin dashboard.
        """
        event_counts = {}
        for e in self._events:
            event_counts[e.event_type] = event_counts.get(e.event_type, 0) + 1

        high_risk_events = [
            e.to_dict() for e in self._events if e.severity == "HIGH"
        ]

        return {
            "report_id":     str(uuid.uuid4()),
            "generated_at":  datetime.now(timezone.utc).isoformat(),
            "session": {
                "candidate_id":  self.candidate_id,
                "session_id":    self.session_id,
                "started_at":    self._session_start,
                "total_frames":  self._frame_counter,
                "total_events":  len(self._events),
            },
            "risk_analysis": {
                "risk_score":        self._engine.score,
                "risk_level":        self._engine.classify(),
                "flags":             list(self._flags),
                "event_breakdown":   event_counts,
                "high_risk_events":  high_risk_events,
            },
            "full_event_log": [e.to_dict() for e in self._events],
        }

    def reset_session(self):
        """Reset for a fresh candidate/session."""
        self._engine.reset()
        self._events.clear()
        self._flags.clear()
        self._frame_counter = 0
        self._session_start = datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────
# 5. INTEGRATION SHIM FOR EXISTING YOLO CODE
# ─────────────────────────────────────────────

class ProctoringLogger:
    """
    Drop-in replacement for the original ProctoringLogger.
    Wraps AssessmentDataMapper to emit structured logs.
    """

    def __init__(self, mapper: AssessmentDataMapper):
        self._mapper = mapper

    def emit_event(self, v_type: str, confidence: float, metadata: Optional[dict] = None) -> dict:
        output = self._mapper.record_event(v_type, confidence, extra_metadata=metadata)
        score = output["risk_analysis"]["risk_score"]
        level = output["risk_analysis"]["risk_level"]
        print(f"📡 [{level}] {v_type} | conf={confidence:.2f} | risk={score}%")
        return output


# ─────────────────────────────────────────────
# 6. DEMO / SMOKE TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    mapper = AssessmentDataMapper(
        candidate_id="CAND-1042",
        session_id="SESSION-9981",
        question_id="Q3",
    )
    logger = ProctoringLogger(mapper)

    # Simulate a sequence of events from the CV pipeline
    events = [
        ("LOOKING_AWAY",    0.80),
        ("BAD_POSTURE",     0.65),
        ("PHONE",           0.92),
        ("MULTIPLE_PERSONS",1.00),
        ("NO_FACE",         0.95),
    ]

    print("\n=== Per-Event Structured Output ===\n")
    for ev, conf in events:
        result = logger.emit_event(ev, conf)
        print(json.dumps(result, indent=2))
        print("-" * 60)

    print("\n=== Final Session Report ===\n")
    report = mapper.generate_report()
    print(json.dumps(report, indent=2))