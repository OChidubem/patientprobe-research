import wave
import numpy as np
import pytest
from patientprobe.audio import RATE, Channel, combine_stereo, save_mp3


def test_two_channels_are_preserved_and_aligned(tmp_path):
    l = Channel()
    r = Channel()
    l.add(np.array([100, -100, 200], dtype=np.int16), 3)
    r.add(np.array([400, 500], dtype=np.int16), 6)
    stereo = combine_stereo(l, r)
    assert stereo.shape == (6, 2)
    assert stereo[:3, 0].tolist() == [100, -100, 200]
    assert stereo[:4, 1].tolist() == [0, 0, 0, 0]
    assert stereo[4:, 1].tolist() == [400, 500]


def test_empty_recording_rejected():
    with pytest.raises(ValueError):
        combine_stereo(Channel(), Channel())


def test_mp3_encoding(tmp_path):
    import shutil
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg unavailable")
    source = np.zeros((RATE, 2), dtype=np.int16)
    wav = tmp_path / "call.wav"
    mp3 = tmp_path / "call.mp3"
    save_mp3(source, wav, mp3)
    assert mp3.stat().st_size > 500
    with wave.open(str(wav)) as f:
        assert f.getnchannels() == 2
        assert f.getframerate() == RATE
