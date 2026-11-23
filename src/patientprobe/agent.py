"""LiveKit Agents STT -> text LLM -> TTS caller. No realtime or hosted agent API."""
from __future__ import annotations
import asyncio
import json
import logging
import re
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, AutoSubscribe, JobContext, cli, TurnHandlingOptions
from livekit.plugins import deepgram, openai, silero

from .config import AGENT_NAME, load_settings
from .prompts import patient_prompt
from .scenarios import get_scenario
from .transcripts import save_turn

load_dotenv(override=False)
log = logging.getLogger("patientprobe.agent")
server = AgentServer()


class SyntheticPatient(Agent):
    def __init__(self, instructions: str):
        super().__init__(instructions=instructions)


@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext):
    meta = json.loads(ctx.job.metadata)
    scenario = get_scenario(meta["scenario"])
    out = Path(meta["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    turns_path = out / "turns.jsonl"
    config = load_settings()

    # Connect before accepting the call; ignore the passive recording participant.
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    log.info("Waiting for authorized test SIP participant for %s", scenario.key)
    await asyncio.wait_for(ctx.wait_for_participant(identity="evaluation-peer"), timeout=85)

    speech_heard = asyncio.Event()
    recent_turns: list[tuple[str, bool]] = []

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en-US", interim_results=True,
                        punctuate=True, smart_format=True),
        llm=openai.LLM(model=config.llm_model, temperature=0.4),
        tts=openai.TTS(model=config.tts_model, voice=config.tts_voice,
                       instructions="Sound like an ordinary adult patient: warm, concise, natural pauses."),
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(
            turn_detection="stt",  # Dedicated STT: no realtime/speech-to-speech model
            endpointing={"mode": "fixed", "min_delay": 0.55, "max_delay": 2.2},
            interruption={"mode": "vad", "min_duration": 0.55,
                          "false_interruption_timeout": 1.4, "resume_false_interruption": True},
        ),
    )

    @session.on("conversation_item_added")
    def item_added(event):
        item = event.item
        if getattr(item, "type", "") != "message":
            return
        role = getattr(item, "role", "")
        text = getattr(item, "text_content", None)
        if text:
            save_turn(turns_path, role, text, event.created_at,
                      interrupted=bool(getattr(item, "interrupted", False)))
            farewell = bool(re.search(r"\b(goodbye|bye|take care|have a good day)\b", text.lower()))
            recent_turns.append((role, farewell))
            # Both parties exchanged closing words, not a one-question hang-up.
            if (len(recent_turns) >= 6
                    and any(r == "assistant" and b for r, b in recent_turns[-4:])
                    and any(r == "user" and b for r, b in recent_turns[-4:])):
                (out / "call_complete.flag").write_text("both parties exchanged farewells\n")

    @session.on("user_input_transcribed")
    def on_receptionist_words(event):
        if event.transcript.strip():
            speech_heard.set()

    @session.on("error")
    def on_error(event):
        # Avoid leaking API keys; capture just the event type for diagnostics.
        log.error("Pipeline error event: %s", type(getattr(event, "error", None)).__name__)

    await session.start(agent=SyntheticPatient(patient_prompt(scenario)), room=ctx.room,
                        record=False)

    # The phone receptionist usually greets first. If silent, take the initiative.
    await asyncio.sleep(4.0)
    if not speech_heard.is_set():
        await session.generate_reply(instructions=(
            "The phone line is quiet. Politely say hello and state your appointment or question "
            "from your current scenario in one short sentence."
        ))

    # The runner terminates the room; close only after SIP has left or a safety timeout.
    sip_departed = asyncio.Event()

    @ctx.room.on("participant_disconnected")
    def participant_left(participant):
        if participant.identity == "evaluation-peer":
            sip_departed.set()

    try:
        await asyncio.wait_for(sip_departed.wait(), timeout=config.max_seconds + 100)
    except asyncio.TimeoutError:
        log.warning("Call exceeded agent safety timeout")
    finally:
        await session.aclose()


if __name__ == "__main__":
    cli.run_app(server)
