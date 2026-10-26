"""Credential boundaries: reject sensitive evidence; redact logs and exports.

Source text and content hashes are never silently rewritten. Existing local
records are not migrated or erased; suspicious source evidence fails closed.
"""
import json
import os
import re

GOOGLE_KEY = re.compile(r"AIza[A-Za-z0-9_-]{35}")
ASSIGNMENT = re.compile(r"(?i)(\b(?:api[_ -]?key|access[_ -]?token|authorization)\s*[:=]\s*)(?:Bearer\s+)?(?:\"[^\"]*\"|'[^']*'|[^\s,;}]+)")
CREDENTIAL_FIELD = re.compile(r"(?i)(?:(?:gemini|google)[_ -]?)?(?:api[_ -]?key|access[_ -]?token|authorization)")
BEARER = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/-]{8,}=*")


class SensitiveDataError(ValueError):
    def __init__(self):
        super().__init__("Credential material is not permitted in source evidence or stored payloads.")


def configured_secrets(extra=()):
    return tuple(sorted({value for value in (*extra, os.environ.get("GEMINI_API_KEY"),
                         os.environ.get("GOOGLE_API_KEY")) if isinstance(value, str) and value}, key=len, reverse=True))


def _strings(value):
    if isinstance(value, str):
        yield value
        # Stored JSON may already escape quotes/backslashes in a known secret.
        try:
            parsed = json.loads(value)
        except (ValueError, RecursionError):
            return
        if isinstance(parsed, (dict, list)):
            yield from _strings(parsed)
        elif isinstance(parsed, str) and parsed != value:
            yield parsed
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


def contains_credentials(value, *, extra=()):
    secrets = configured_secrets(extra)
    return any(GOOGLE_KEY.search(text) or any(secret in text for secret in secrets) for text in _strings(value))


def reject_credentials(value, *, extra=()):
    if contains_credentials(value, extra=extra):
        raise SensitiveDataError()


def redact_text(value, *, extra=()):
    for secret in configured_secrets(extra):
        value = value.replace(secret, "[redacted]")
        # Also cover serialised JSON fragments received as strings in logs.
        escaped = json.dumps(secret)[1:-1]
        value = value.replace(escaped, "[redacted]")
    value = GOOGLE_KEY.sub("[redacted]", value)
    value = ASSIGNMENT.sub(lambda m: m.group(1) + "[redacted]", value)
    return BEARER.sub(lambda m: m.group(1) + "[redacted]", value)


def redact(value, *, extra=()):
    if isinstance(value, str):
        return redact_text(value, extra=extra)
    if isinstance(value, dict):
        return {redact_text(str(key), extra=extra): "[redacted]" if CREDENTIAL_FIELD.fullmatch(str(key))
                else redact(item, extra=extra) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [redact(item, extra=extra) for item in value]
    return value
