import pytest
from patientprobe.scenarios import SCENARIOS, DEFAULT_KEYS, get_scenario
from patientprobe.prompts import patient_prompt


def test_distinct_scenarios_and_natural_goals():
    assert len(SCENARIOS) >= 10
    assert len(set(s.key for s in SCENARIOS)) == len(SCENARIOS)
    assert len(DEFAULT_KEYS) == 10
    for scenario in SCENARIOS:
        assert len(scenario.beats) >= 3
        prompt = patient_prompt(scenario)
        assert scenario.opening in prompt
        assert "not an evaluator" in prompt
        assert "1 to 3 minute" in prompt


def test_unknown_scenario():
    with pytest.raises(ValueError):
        get_scenario("nonexistent")
