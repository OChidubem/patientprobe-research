"""Audio-derived conversational flow metrics. Estimates, not word-level timings."""
from __future__ import annotations
import json
import wave
from pathlib import Path
import numpy as np

FRAME_MS = 20


def _smooth_speech(mask: np.ndarray, *, fill_gap: int = 10, min_run: int = 5) -> np.ndarray:
    """Fill <200ms pauses, reject <100ms noise bursts."""
    a = mask.astype(bool).copy()
    i = 0
    while i < len(a):
        j = i + 1
        while j < len(a) and a[j] == a[i]:
            j += 1
        if not a[i] and i > 0 and j < len(a) and j - i <= fill_gap:
            a[i:j] = True
        i = j
    i = 0
    while i < len(a):
        j = i + 1
        while j < len(a) and a[j] == a[i]:
            j += 1
        if a[i] and j - i < min_run:
            a[i:j] = False
        i = j
    return a


def _intervals(mask: np.ndarray) -> list[tuple[float, float]]:
    starts = np.flatnonzero(mask & ~np.r_[False, mask[:-1]])
    stops = np.flatnonzero(mask & ~np.r_[mask[1:], False])
    return [(round(float(s * FRAME_MS / 1000), 3),
             round(float((e + 1) * FRAME_MS / 1000), 3)) for s, e in zip(starts, stops)]


def measure_audio(stereo: np.ndarray, rate: int) -> dict:
    """Estimates talk time and inter-speaker gaps using adaptive frame-energy VAD.

    Frame-energy VAD is intentionally only an explanatory QA signal: noise can
    change thresholds, and overlap does not by itself imply unwanted barge-in.
    """
    if stereo.ndim != 2 or stereo.shape[1] != 2:
        raise ValueError("Expected stereo audio [samples, 2]")
    frame = max(1, int(rate * FRAME_MS / 1000))
    usable = (len(stereo) // frame) * frame
    if usable < frame:
        return {"warning": "Insufficient audio for flow analysis"}
    windows = stereo[:usable].astype(np.float64).reshape(-1, frame, 2)
    rms = np.sqrt(np.mean(np.square(windows), axis=1))
    masks = []
    for channel in range(2):
        levels = rms[:, channel]
        floor = float(np.percentile(levels, 15))
        threshold = max(180.0, min(float(np.percentile(levels, 90)) * 0.45, max(300.0, floor * 3.5)))
        masks.append(_smooth_speech(levels > threshold))
    patient, receptionist = masks
    spans = [_intervals(mask) for mask in masks]
    active = patient | receptionist
    overlap = patient & receptionist
    speech_frames = max(1, int(active.sum()))
    # A candidate response is an utterance beginning after an utterance of the other speaker.
    # Ignore very long gaps because they may reflect hold/music/ringing.
    delays: dict[str, list[float]] = {"patient_after_receptionist": [],
                                      "receptionist_after_patient": []}
    for role, previous in (("patient_after_receptionist", 1), ("receptionist_after_patient", 0)):
        following = 1 - previous
        for _start, end in spans[previous]:
            gaps = [round(start - end, 3) for start, _ in spans[following] if 0 <= start - end <= 6]
            if gaps:
                delays[role].append(min(gaps))
    return {
        "duration_s": round(len(stereo) / rate, 2),
        "speech_seconds": {
            "patient": round(float(patient.sum()) * FRAME_MS / 1000, 2),
            "receptionist": round(float(receptionist.sum()) * FRAME_MS / 1000, 2),
        },
        "utterances_estimated": {"patient": len(spans[0]), "receptionist": len(spans[1])},
        "overlap_fraction_of_speech": round(float(overlap.sum()) / speech_frames, 3),
        "median_reply_gap_seconds_estimated": {
            role: round(float(np.median(v)), 2) if v else None for role, v in delays.items()
        },
        "method": ("20ms frame RMS energy VAD; approximate only, does not measure semantic "
                   "correctness or detect whether interruption was appropriate"),
    }


def metrics_from_wav(wav_path: Path, json_path: Path) -> dict:
    with wave.open(str(wav_path), "rb") as f:
        if f.getnchannels() != 2 or f.getsampwidth() != 2:
            raise ValueError("Expected two-channel 16-bit PCM WAV")
        data = np.frombuffer(f.readframes(f.getnframes()), dtype="<i2").reshape(-1, 2)
        result = measure_audio(data, f.getframerate())
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
