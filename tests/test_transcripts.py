import json
from patientprobe.transcripts import save_turn, read_turns, write_transcript, evidence_status, format_timestamp


def test_two_sided_transcript_and_relative_times(tmp_path):
    p = tmp_path / "turns.jsonl"
    save_turn(p, "assistant", "I need an appointment", 105.0)
    save_turn(p, "user", "What day works for you?", 110.0)
    save_turn(p, "function", "ignore", 111.0)
    turns = read_turns(p)
    assert len(turns) == 2
    write_transcript(tmp_path / "transcript.txt", turns, 100.0)
    txt = (tmp_path / "transcript.txt").read_text()
    assert "[00:05] PATIENT: I need an appointment" in txt
    assert "[00:10] RECEPTIONIST: What day works for you?" in txt
    assert format_timestamp(65) == "01:05"


def test_qc_needs_both_sides_real_audio_and_time(tmp_path):
    turns = [{"role": "user", "text": "answer " * 35},
             {"role": "assistant", "text": "question " * 45}]
    mp3 = tmp_path / "recording.mp3"
    mp3.write_bytes(b"X" * 16000)
    assert evidence_status(turns, mp3, 70)["meets_minimum_full_call"]
    assert not evidence_status(turns, mp3, 12)["meets_minimum_full_call"]
    assert not evidence_status(turns[:1], mp3, 70)["meets_minimum_full_call"]
    mp3.unlink()
    assert not evidence_status(turns, mp3, 70)["meets_minimum_full_call"]
