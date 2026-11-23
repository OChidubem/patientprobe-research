from patientprobe.cli import main


def test_cli_prints_scenarios_without_credentials(capsys):
    assert main(["scenarios"]) == 0
    assert "10_safety" in capsys.readouterr().out


def test_no_credentials_means_no_call(monkeypatch, capsys):
    for key in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY",
                "DEEPGRAM_API_KEY", "LIVEKIT_SIP_TRUNK_ID", "SIP_FROM_NUMBER", "PATIENTPROBE_APPROVED_DESTINATION", "PATIENTPROBE_ENABLE_LIVE_CALLS"):
        monkeypatch.delenv(key, raising=False)
    assert main(["run", "01_schedule", "--confirm-live-calls"]) == 2
    assert "Configuration error" in capsys.readouterr().err
