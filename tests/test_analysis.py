import json
import pytest
from patientprobe.analysis import prepare_evidence, bug_report


def test_prepare_evidence_rejects_missing_transcript(tmp_path):
    (tmp_path / "scenario.json").write_text(json.dumps({"key": "01_schedule"}))
    with pytest.raises(ValueError, match="No real call transcript"):
        prepare_evidence(tmp_path)


def test_bug_report_uses_manual_approval_only(tmp_path):
    folder = tmp_path / "call_01"
    folder.mkdir()
    (folder / "qa_review.json").write_text('{"issues":[{"title":"made up"}]}')
    output = tmp_path / "BUGS.md"
    assert bug_report([folder], output) == 0
    assert "No findings have been manually verified" in output.read_text()
    (folder / "approved_bugs.json").write_text(json.dumps([{
        "title": "Unverified Sunday booking", "severity": "High", "timestamp": "01:23",
        "evidence": "Patient requested Sunday; agent said booked without verifying hours",
        "expected": "Check hours", "impact": "Potential wasted patient visit",
    }]))
    assert bug_report([folder], output) == 1
    assert "BUG-01" in output.read_text()
