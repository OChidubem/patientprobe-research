"""Local configuration; no real endpoints or secrets are included in the repository."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from .safety import validate_caller_id, validate_destination

AGENT_NAME = "patientprobe-caller"


@dataclass(frozen=True)
class Settings:
    livekit_url: str
    livekit_key: str
    livekit_secret: str
    sip_trunk_id: str
    caller_id: str
    authorized_destination: str
    live_calls_enabled: bool
    openai_key: str
    deepgram_key: str
    artifacts_dir: Path
    max_seconds: int
    llm_model: str
    tts_model: str
    tts_voice: str


def load_settings(*, require_live: bool = True) -> Settings:
    load_dotenv(override=False)
    s = Settings(
        livekit_url=os.getenv("LIVEKIT_URL", ""),
        livekit_key=os.getenv("LIVEKIT_API_KEY", ""),
        livekit_secret=os.getenv("LIVEKIT_API_SECRET", ""),
        sip_trunk_id=os.getenv("LIVEKIT_SIP_TRUNK_ID", ""),
        caller_id=os.getenv("SIP_FROM_NUMBER", ""),
        authorized_destination=os.getenv("PATIENTPROBE_APPROVED_DESTINATION", ""),
        live_calls_enabled=os.getenv("PATIENTPROBE_ENABLE_LIVE_CALLS", "false").lower() == "true",
        openai_key=os.getenv("OPENAI_API_KEY", ""),
        deepgram_key=os.getenv("DEEPGRAM_API_KEY", ""),
        artifacts_dir=Path(os.getenv("PATIENTPROBE_ARTIFACTS", "artifacts/calls")),
        max_seconds=int(os.getenv("PATIENTPROBE_MAX_SECONDS", "175")),
        llm_model=os.getenv("PATIENTPROBE_LLM_MODEL", "gpt-4.1-mini"),
        tts_model=os.getenv("PATIENTPROBE_TTS_MODEL", "gpt-4o-mini-tts"),
        tts_voice=os.getenv("PATIENTPROBE_TTS_VOICE", "ash"),
    )
    if not 65 <= s.max_seconds <= 190:
        raise ValueError("PATIENTPROBE_MAX_SECONDS must be between 65 and 190")
    if require_live:
        required = {
            "LIVEKIT_URL": s.livekit_url,
            "LIVEKIT_API_KEY": s.livekit_key,
            "LIVEKIT_API_SECRET": s.livekit_secret,
            "LIVEKIT_SIP_TRUNK_ID": s.sip_trunk_id,
            "SIP_FROM_NUMBER": s.caller_id,
            "PATIENTPROBE_APPROVED_DESTINATION": s.authorized_destination,
            "OPENAI_API_KEY": s.openai_key,
            "DEEPGRAM_API_KEY": s.deepgram_key,
        }
        missing = [key for key, value in required.items() if not value or
                   value.startswith('your_') or 'your-project' in value or
                   value.startswith('ST_your_')]
        if missing:
            raise ValueError("Missing configuration: " + ", ".join(missing))
        validate_destination(s.authorized_destination, s.authorized_destination,
                             enabled=s.live_calls_enabled)
        validate_caller_id(s.caller_id, s.authorized_destination)
    return s
