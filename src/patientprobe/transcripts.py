"""Persist committed transcripts, with relative timestamps and evidence checks."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path


def save_turn(path: Path, role: str, text: str, ts: float, interrupted: bool = False) -> None:
    if role not in ("user", "assistant") or not text.strip():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"role": role, "text": text, "ts": ts,
                            "interrupted": interrupted}, ensure_ascii=False) + "\n")


def read_turns(path: Path) -> list[dict]:
    if not path.exists():
        return []
    turns = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sorted(turns, key=lambda item: item["ts"])


def format_timestamp(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60:02}:{seconds % 60:02}"


def write_transcript(path: Path, turns: list[dict], base_ts: float) -> None:
    lines = ["# Two-sided conversation transcript", "", "Caller = synthetic patient", "Receptionist = system under test", "",
             "Times are approximate: SDK transcript commit times, not word-level audio alignment.", ""]
    for t in turns:
        label = "PATIENT" if t["role"] == "assistant" else "RECEPTIONIST"
        interrupted = " [interrupted]" if t.get("interrupted") else ""
        lines.append(f"[{format_timestamp(t['ts'] - base_ts)}] {label}{interrupted}: {t['text']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evidence_status(turns: list[dict], mp3: Path, duration_s: float) -> dict:
    roles = {t.get("role") for t in turns if t.get("text", "").strip()}
    words = {r: sum(len(t.get("text", "").split()) for t in turns if t.get("role") == r)
             for r in ("user", "assistant")}
    audio = mp3.exists() and mp3.stat().st_size > 12_000
    return {
        "audio_mp3_present": audio,
        "both_sides_present": roles == {"user", "assistant"},
        "duration_seconds": round(duration_s, 1),
        "meets_minimum_full_call": audio and roles == {"user", "assistant"} and duration_s >= 60 and min(words.values()) >= 30,
        "word_count": words,
        "notes": "Minimum thresholds are a screening aid; manually listen to verify coherence.",
    }


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
