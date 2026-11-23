import numpy as np
import pytest
from patientprobe.metrics import measure_audio


def test_metrics_sequential_exchange():
    rate = 16000
    x = np.zeros((rate * 4, 2), dtype=np.int16)
    # Patient speaks at .5-1.25; receptionist at 2-2.75
    x[rate // 2 : int(rate * 1.25), 0] = 5000
    x[rate * 2 : int(rate * 2.75), 1] = 5000
    metrics = measure_audio(x, rate)
    assert metrics["speech_seconds"]["patient"] > 0.5
    assert metrics["speech_seconds"]["receptionist"] > 0.5
    assert metrics["overlap_fraction_of_speech"] == 0
    assert metrics["utterances_estimated"] == {"patient": 1, "receptionist": 1}
    assert 0.5 < metrics["median_reply_gap_seconds_estimated"]["receptionist_after_patient"] < 1.0


def test_rejects_mono():
    with pytest.raises(ValueError):
        measure_audio(np.zeros((100, 1)), 16000)
