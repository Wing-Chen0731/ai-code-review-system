import re

SENSITIVE_PATTERNS = [
    (r'(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*["\']?[\w\-]+', r"\1=***REDACTED***"),
    (r"(?i)bearer\s+[\w\-.]+", "Bearer ***REDACTED***"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "***EMAIL***"),
    (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "***CARD***"),
]


def redact_sensitive(text: str) -> str:
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text

