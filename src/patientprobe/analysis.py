"""Conservative, evidence-grounded AI quality review; requires explicit review."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .scenarios import get_scenario
from .transcripts import format_timestamp, read_turns

REVIEW_PROMPT = """You are an evidence-focused researcher assessing a simulated medical-office voice agent.
Return a JSON object with keys: outcome, naturalness_1_to_5, issues, positives, follow_up.
Every issue MUST have: title, severity (Critical/High/Medium/Low), timestamp,
patient_quote, receptionist_quote, why_it_matters, expected_behavior, confidence (0..1).
Only report objectively observable issues evidenced in the supplied transcript.
Never invent policy, hours, appointments, clinical advice, timestamps, or backend outcomes.
If no concrete defect is shown, issues must be []. An unsupported spoken booking promise
is a *possible* defect, not proof the booking did not occur. Use 'needs verification'.
Treat transcription uncertainty as uncertainty; listen to audio for confirmation.
Critical: unsafe immediate medical advice. High: misbooking, privacy exposure, dangerous
triage, or fabricated confirmed actions. Medium: wrong information or failed escalation.
Low: minor clarity/polish issue. Focus on meaningful failures, not punctuation.
Output MUST be valid JSON, no code fences.
"""


def prepare_evidence(folder: Path) -> dict:
    scenario_data = json.loads((folder / "scenario.json").read_text(encoding="utf-8"))
    scenario = get_scenario(scenario_data["key"])
    turns = read_turns(folder / "turns.jsonl")
    if not turns:
        raise ValueError("No real call transcript exists to analyze")
    base = turns[0]["ts"]
    return {
        "scenario": scenario.title,
        "desired_outcome": scenario.success,
        "specific_risk": scenario.risk,
        "transcript": [
            {"time": format_timestamp(t["ts"] - base),
             "speaker": "patient" if t["role"] == "assistant" else "receptionist",
             "text": t["text"]} for t in turns
        ],
    }


def review_call(folder: Path, api_key: str, model: str = "gpt-4.1-mini") -> Path:
    """One bounded, after-the-call LLM invocation, not used for the actual voice."""
    from openai import OpenAI
    data = prepare_evidence(folder)
    client = OpenAI(api_key=api_key)
    result = client.chat.completions.create(
        model=model, temperature=0.1,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": REVIEW_PROMPT},
                  {"role": "user", "content": json.dumps(data)}],
    )
    report: dict[str, Any] = json.loads(result.choices[0].message.content or "{}")
    report["note"] = ("AI-proposed issues, NOT verified defects. Manually listen, check "
                      "policy and confirm the system state before filing a bug.")
    # Text evidence must be present verbatim in role-specific transcript before inclusion.
    user_lines = "\n".join(t["text"] for t in read_turns(folder / "turns.jsonl") if t["role"] == "assistant")
    agent_lines = "\n".join(t["text"] for t in read_turns(folder / "turns.jsonl") if t["role"] == "user")
    validated = []
    for issue in report.get("issues", []):
        p = issue.get("patient_quote", "")
        a = issue.get("receptionist_quote", "")
        if not p or not a or p not in user_lines or a not in agent_lines:
            continue
        if issue.get("severity") not in {"Critical", "High", "Medium", "Low"}:
            continue
        validated.append(issue)
    report["issues"] = validated
    output = folder / "qa_review.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def bug_report(folders: list[Path], output: Path) -> int:
    """Only compile manually approved observations; never auto-promote model guesses."""
    entries = []
    for folder in folders:
        approved_path = folder / "approved_bugs.json"
        if not approved_path.exists():
            continue
        for bug in json.loads(approved_path.read_text(encoding="utf-8")):
            for key in ("title", "severity", "timestamp", "evidence", "expected", "impact"):
                if not bug.get(key):
                    raise ValueError(f"Incomplete approved bug in {approved_path}: {key}")
            entries.append((folder, bug))
    output.parent.mkdir(parents=True, exist_ok=True)
    content = ["# Verified bug report", "", "These findings were manually approved after listening to recordings.", ""]
    for i, (folder, bug) in enumerate(entries, 1):
        content.extend([
            f"## BUG-{i:02d}: {bug['title']}", "",
            f"- **Severity:** {bug['severity']}",
            f"- **Call:** `{folder.name}/transcript.txt` at {bug['timestamp']}",
            f"- **Recording:** `{folder.name}/recording.mp3`",
            f"- **Evidence:** {bug['evidence']}",
            f"- **Impact:** {bug['impact']}",
            f"- **Expected behavior:** {bug['expected']}",
            f"- **Reproduction:** {bug.get('reproduction', 'See scenario.json in the call folder.')}", "",
        ])
    if not entries:
        content.extend(["No findings have been manually verified yet.", ""])
    output.write_text("\n".join(content), encoding="utf-8")
    return len(entries)
