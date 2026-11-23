"""Independent two-sided recorder. Stereo: left=patient, right=receptionist.

A passive LiveKit participant subscribes to BOTH audio tracks. Frames are aligned
on a shared monotonic clock; MP3 is exported via ffmpeg. This avoids depending
on LiveKit Insights' manual recording downloads or third-party storage.
"""
from __future__ import annotations
import asyncio
import shutil
import subprocess
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

RATE = 16_000


@dataclass
class Channel:
    chunks: list[tuple[int, np.ndarray]] = field(default_factory=list)
    end_sample: int = 0

    def add(self, pcm: np.ndarray, observed_sample: int) -> None:
        # Most chunks arrive 20ms apart. Absorb network jitter under 200ms;
        # preserve longer gaps as actual silence rather than compressing pauses.
        if self.chunks:
            start = max(self.end_sample, observed_sample) if observed_sample - self.end_sample > RATE // 5 else self.end_sample
        else:
            start = max(0, observed_sample - len(pcm))
        copy = np.array(pcm, dtype=np.int16, copy=True)
        self.chunks.append((start, copy))
        self.end_sample = start + len(copy)


def combine_stereo(left: Channel, right: Channel) -> np.ndarray:
    end = max(left.end_sample, right.end_sample)
    if end == 0:
        raise ValueError("No audio captured — cannot create a recording")
    out = np.zeros((end, 2), dtype=np.int16)
    for ch, index in ((left, 0), (right, 1)):
        for start, samples in ch.chunks:
            length = min(len(samples), end - start)
            if length > 0:
                out[start:start + length, index] = samples[:length]
    return out


def save_mp3(stereo: np.ndarray, wav_path: Path, mp3_path: Path) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for MP3 output; install it before calling")
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav_path), "wb") as wave_file:
        wave_file.setnchannels(2)
        wave_file.setsampwidth(2)
        wave_file.setframerate(RATE)
        wave_file.writeframes(stereo.astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav_path),
                    "-codec:a", "libmp3lame", "-b:a", "96k", str(mp3_path)], check=True)


class TwoSidedRecorder:
    """Monitor room without publishing audio. Caller track is evaluation-peer; other is simulated patient."""

    def __init__(self, room_name: str, out: Path, *, started_at: float | None = None):
        from livekit import rtc
        self.rtc = rtc
        self.room_name = room_name
        self.out = out
        self.room = rtc.Room()
        self.origin = started_at or time.monotonic()
        self.left = Channel()       # patient's AI voice
        self.right = Channel()      # remote receptionist
        self.tasks: set[asyncio.Task] = set()
        self.streams = []
        self.sip_left = asyncio.Event()
        self.sip_joined = asyncio.Event()
        self.agent_joined = asyncio.Event()
        self.track_roles: set[str] = set()

        @self.room.on("participant_connected")
        def participant_joined(participant):
            if participant.identity == "evaluation-peer":
                self.sip_joined.set()
            elif not participant.identity.startswith("recorder-"):
                self.agent_joined.set()

        @self.room.on("participant_disconnected")
        def participant_left(participant):
            if participant.identity == "evaluation-peer":
                self.sip_left.set()

        @self.room.on("track_subscribed")
        def track_subscribed(track, _publication, participant):
            if track.kind != rtc.TrackKind.KIND_AUDIO:
                return
            role = "receptionist" if participant.identity == "evaluation-peer" else "patient"
            if participant.identity.startswith("recorder-"):
                return
            stream = rtc.AudioStream(track, sample_rate=RATE, num_channels=1)
            self.streams.append(stream)
            task = asyncio.create_task(self._capture(stream, role))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
            self.track_roles.add(role)

    async def connect(self, url: str, key: str, secret: str) -> None:
        from livekit import api
        token = (api.AccessToken(key, secret)
                 .with_identity("recorder-" + self.room_name[-12:])
                 .with_grants(api.VideoGrants(room_join=True, room=self.room_name,
                                              can_subscribe=True, can_publish=False))
                 .to_jwt())
        await self.room.connect(url, token)
        for p in self.room.remote_participants.values():
            if p.identity == "evaluation-peer":
                self.sip_joined.set()
            elif not p.identity.startswith("recorder-"):
                self.agent_joined.set()

    async def _capture(self, stream, role: str) -> None:
        try:
            async for event in stream:
                frame = event.frame
                data = np.frombuffer(frame.data, dtype=np.int16)
                now_sample = int((time.monotonic() - self.origin) * RATE)
                ch = self.right if role == "receptionist" else self.left
                ch.add(data, now_sample)
        except asyncio.CancelledError:
            raise

    async def close(self) -> None:
        for stream in self.streams:
            try:
                await stream.aclose()
            except Exception:
                pass
        for task in list(self.tasks):
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.room.disconnect()

    def export(self) -> Path:
        mp3 = self.out / "recording.mp3"
        audio = combine_stereo(self.left, self.right)
        # Room creation and ringing may precede the actual conversation by a minute.
        # Crop leading silence, retaining a full second before the first audible sound.
        peak = np.max(np.abs(audio.astype(np.int32)), axis=1)
        audible = np.flatnonzero(peak > 160)
        if len(audible):
            crop = max(0, int(audible[0]) - RATE)
            audio = audio[crop:]
        save_mp3(audio, self.out / "recording.wav", mp3)
        return mp3
