"""Unit tests use invented values, never real telephone destinations."""
import pytest
from patientprobe.safety import validate_destination, validate_caller_id

# Synthetic E.164-shaped identifiers, not actual dial destinations.
TEST_TARGET = "+" + "1" * 11
TEST_CALLER = "+" + "2" * 11


def test_live_calls_disabled_by_default():
    with pytest.raises(ValueError, match="disabled"):
        validate_destination(TEST_TARGET, TEST_TARGET, enabled=False)


def test_destination_requires_exact_authorized_match():
    assert validate_destination(TEST_TARGET, TEST_TARGET, enabled=True) == TEST_TARGET
    for number in (TEST_CALLER, TEST_TARGET + " ", "", "n/a"):
        with pytest.raises(ValueError):
            validate_destination(number, TEST_TARGET, enabled=True)
    with pytest.raises(ValueError):
        validate_destination(TEST_TARGET, "", enabled=True)


def test_caller_id_validity_and_separation():
    assert validate_caller_id(TEST_CALLER, TEST_TARGET) == TEST_CALLER
    for value in ("", "no", "1" * 11, TEST_TARGET):
        with pytest.raises(ValueError):
            validate_caller_id(value, TEST_TARGET)
