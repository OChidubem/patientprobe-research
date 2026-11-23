"""Opt-in telephony safeguards for authorized research test endpoints.

No destination is shipped with the public code. Configuring an approved endpoint
must occur locally; this module NEVER selects a target or dials a number.
"""
import re

_E164 = re.compile(r"\+[1-9]\d{7,14}\Z")


def validate_destination(number: str, approved_destination: str, *, enabled: bool) -> str:
    if not enabled:
        raise ValueError("Live calling is disabled; opt in explicitly in your private .env")
    if not approved_destination or not _E164.fullmatch(approved_destination):
        raise ValueError("Configure an authorized E.164 test endpoint locally")
    if number != approved_destination:
        raise ValueError("Destination is not the configured authorized test endpoint")
    return number


def validate_caller_id(number: str, approved_destination: str = "") -> str:
    if not _E164.fullmatch(number):
        raise ValueError("SIP_FROM_NUMBER must be a valid E.164 caller ID")
    if approved_destination and number == approved_destination:
        raise ValueError("Caller ID must differ from the approved test endpoint")
    return number
