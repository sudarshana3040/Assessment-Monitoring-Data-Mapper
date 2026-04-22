# Assessment-Monitoring-Data-Mapper
The Assessment Monitoring Data Mapper converts real-time proctoring events into structured logs and risk analysis. It assigns scores based on event severity, classifies risk levels, and generates organized outputs for monitoring, evaluation, and ensuring fairness during assessments.
📘 Assessment Monitoring Data Mapper
📌 Overview

The Assessment Monitoring Data Mapper is a module designed to convert raw proctoring data into structured logs and risk-related insights. It plays a key role in ensuring fairness and integrity during AI-based assessments by analyzing candidate behavior in real time.

🎯 Objective
Convert monitoring events into structured data
Assign risk scores based on event severity
Classify candidate behavior into risk levels
Generate outputs for backend systems and admin review
⚙️ Features
📄 Event Logging: Captures all monitoring events with metadata
⚠️ Risk Scoring: Assigns weighted scores based on severity
📊 Risk Classification: LOW / MEDIUM / HIGH levels
🚩 Flagging System: Identifies suspicious activities
🧾 Structured JSON Output: Clean format for storage and analysis
📈 Session Report: Summary of all events and overall risk
🧠 Mapping Logic

Each event is mapped with:

Score (impact on risk)
Severity (LOW / MEDIUM / HIGH)
Category (type of behavior)
Example:
Event	Score	Severity	Category
PHONE	60	HIGH	Device Usage
MULTIPLE_PERSONS	55	HIGH	Environment
NO_FACE	30	MEDIUM	Presence
LOOKING_AWAY	15	LOW	Attention
BAD_POSTURE	10	LOW	Posture
🧮 Risk Calculation
Risk score is accumulated based on events
Each event is weighted by confidence
Maximum score is capped at 100
Risk Levels:
LOW: 0–39
MEDIUM: 40–69
HIGH: 70–100
🧾 Output Structure
🔹 Per Event Output
{
  "timestamp": "...",
  "log": {
    "event": "PHONE",
    "confidence": 0.92
  },
  "risk_analysis": {
    "risk_score": 60,
    "risk_level": "HIGH",
    "flags": ["PHONE"]
  }
}
🔹 Final Session Report
{
  "session": {...},
  "risk_analysis": {
    "risk_score": 100,
    "risk_level": "HIGH",
    "flags": ["PHONE", "MULTIPLE_PERSONS"],
    "event_breakdown": {...}
  },
  "full_event_log": [...]
}
🔄 Workflow
Monitoring System → Data Mapper → Structured Output → Backend/Admin
🛠️ Technologies Used
Python
JSON
Computer Vision (YOLO-based detection)
🚀 Usage
mapper = AssessmentDataMapper(candidate_id="C001", session_id="S123")
mapper.record_event("PHONE", confidence=0.92)
report = mapper.generate_report()
print(report)
📊 Applications
Online assessments
AI-based proctoring systems
Candidate behavior analysis
Fraud detection
🧠 Summary

This module transforms raw monitoring signals into meaningful insights by combining logging, risk scoring, and structured reporting, enabling automated and fair evaluation of candidates.

If you want, I can also:

Make short README (1 page)
Add architecture diagram
Convert this into PPT for presentation 👍
