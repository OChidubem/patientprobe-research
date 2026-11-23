"""Opt-in LiveKit dispatch to an authorized test endpoint and private evidence capture."""
from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid
from pathlib import Path

from .audio import TwoSidedRecorder
from .metrics import metrics_from_wav
from .config import AGENT_NAME, Settings
from .safety import validate_caller_id, validate_destination
from .scenarios import get_scenario
from .transcripts import evidence_status, read_turns, utc_iso, write_transcript

log = logging.getLogger("patientprobe.runner")


async def run_call(scenario_key: str, settings: Settings) -> dict:
    from livekit import api

    scenario = get_scenario(scenario_key)
    destination = validate_destination(settings.authorized_destination, settings.authorized_destination,
                                       enabled=settings.live_calls_enabled)
    caller = validate_caller_id(settings.caller_id, destination)
    # Unique directory per attempt avoids overwriting previous evidence.
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    out = (settings.artifacts_dir / f"{scenario.key}_{attempt}").resolve()
    out.mkdir(parents=True, exist_ok=False)
    room_name = f"patientprobe-{uuid.uuid4().hex[:20]}"
    recorder = TwoSidedRecorder(room_name, out)
    answered_epoch = 0.0
    duration = 0.0
    status = "not_started"
    error = None
    result = {}

    (out / "scenario.json").write_text(json.dumps({
        "key": scenario.key, "title": scenario.title, "patient": scenario.patient,
        "goal": scenario.success, "risk": scenario.risk, "beats": scenario.beats,
        "destination": destination, "caller_id": caller,
        "started_utc": utc_iso(), "room": room_name,
    }, indent=2) + "\n", encoding="utf-8")

    async with api.LiveKitAPI() as lk:
        try:
            await recorder.connect(settings.livekit_url, settings.livekit_key, settings.livekit_secret)
            await lk.agent_dispatch.create_dispatch(api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME, room=room_name,
                metadata=json.dumps({"scenario": scenario.key, "output_dir": str(out)}),
            ))
            await asyncio.wait_for(recorder.agent_joined.wait(), timeout=55)
            status = "dialing"
            log.info("Starting authorized research test call for scenario %s", scenario.key)
            await lk.sip.create_sip_participant(api.CreateSIPParticipantRequest(
                sip_trunk_id=settings.sip_trunk_id,
                sip_number=caller,
                sip_call_to=destination,
                room_name=room_name,
                participant_identity="evaluation-peer",
                participant_name="Synthetic test agent",
                wait_until_answered=True,
            ), timeout=80)
            answered_epoch = time.time()
            connected = time.monotonic()
            status = "connected"
            await asyncio.wait_for(recorder.sip_joined.wait(), timeout=10)
            # Stop after natural two-sided farewells OR remote hangup; hard cost cap.
            deadline = connected + settings.max_seconds
            while time.monotonic() < deadline:
                if recorder.sip_left.is_set():
                    status = "remote_hangup"
                    await asyncio.sleep(1.0)
                    break
                if (out / "call_complete.flag").exists():
                    status = "completed_by_dialogue"
                    await asyncio.sleep(5.0)  # Let final TTS / remote goodbye finish.
                    break
                await asyncio.sleep(0.5)
            else:
                status = "time_cap"
            duration = time.monotonic() - connected
        except Exception as exc:
            status = "failed"
            error = f"{type(exc).__name__}: {exc}"
            log.error("Call %s failed: %s", scenario.key, error)
        finally:
            try:
                await recorder.close()
            except Exception as exc:
                error = (error or "") + f"; recorder close: {type(exc).__name__}"
            try:
                await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
            except Exception:
                pass

    audio_path = out / "recording.mp3"
    if recorder.left.chunks and recorder.right.chunks:
        try:
            recorder.export()
            metrics_from_wav(out / "recording.wav", out / "audio_metrics.json")
        except Exception as exc:
            error = (error or "") + f"; audio export: {type(exc).__name__}: {exc}"
    else:
        error = (error or "") + f"; missing audio tracks: {sorted(recorder.track_roles)}"

    turns = read_turns(out / "turns.jsonl")
    # When dial fails, use the earliest committed item as the relative origin.
    origin = answered_epoch or (turns[0]["ts"] if turns else time.time())
    write_transcript(out / "transcript.txt", turns, origin)
    qc = evidence_status(turns, audio_path, duration)
    result = {
        "scenario": scenario.key, "status": status, "duration_s": round(duration, 1),
        "caller_id": caller, "destination": destination,
        "recording": str(audio_path) if audio_path.exists() else None,
        "transcript": str(out / "transcript.txt"), "qc": qc, "error": error,
        "created_utc": utc_iso(),
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
