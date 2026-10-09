import base64
import re
from collections.abc import Iterable
from itertools import islice

_JWT_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]*\."
    r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"""(?ix)
    (["']?(?:password|passwd|pwd|api[_-]?key|access[_-]?token|auth[_-]?token|
    client[_-]?secret|secret)["']?\s*[:=]\s*)
    (?:["'][^"']*["']|[^,\s&;}]+)
    """
)
_PREFIX_KEY_PATTERN = re.compile(r"(?i)\b(?:sk-[A-Za-z0-9_-]{8,}|AIza[A-Za-z0-9_-]{20,})\b")
_HEX_SECRET_PATTERN = re.compile(r"(?i)\b[0-9a-f]{32,}\b")
_LONG_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_+/-])[A-Za-z0-9_+/-]{40,}={0,2}(?![A-Za-z0-9_+/-=])"
)


def _redact_line(value: object) -> str:
    line = str(value)
    line = _JWT_PATTERN.sub("[REDACTED]", line)
    line = _BEARER_PATTERN.sub("Bearer [REDACTED]", line)
    line = _SECRET_ASSIGNMENT_PATTERN.sub(r"\1[REDACTED]", line)
    line = _PREFIX_KEY_PATTERN.sub("[REDACTED]", line)
    line = _HEX_SECRET_PATTERN.sub("[REDACTED]", line)

    def redact_long_token(match: re.Match[str]) -> str:
        token = match.group(0)
        if len(token) >= 40 and len(token) % 4 == 0:
            try:
                if base64.b64decode(token, altchars=b"-_", validate=True):
                    return "[REDACTED]"
            except (ValueError, base64.binascii.Error):
                pass
        return token

    line = _LONG_TOKEN_PATTERN.sub(redact_long_token, line)
    return _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", line)[:500]


def redact_logs(logs: Iterable[object], *, max_lines: int = 200) -> list[str]:
    if max_lines < 0:
        raise ValueError("max_lines must be non-negative")
    return [_redact_line(line) for line in islice(logs, max_lines)]


def redact_text(value: object) -> str:
    return _redact_line(value)
