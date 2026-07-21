"""Lightweight input/output guardrails: prompt-injection heuristics and PII detection.

Regex-based and intentionally simple — enough to demonstrate the pattern and catch the
obvious cases without a paid moderation API."""

import re

_INJECTION_PATTERNS = [
    r"ignore (all|previous|prior|above) (instructions|prompts)",
    r"disregard (the|all|previous) (instructions|context)",
    r"you are now (a|an|no longer)",
    r"reveal your (system )?(prompt|instructions)",
    r"pretend to be",
    r"jailbreak",
]

_PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
    "phone": r"\b(?:\+?\d{1,3}[ -]?)?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4}\b",
}

_injection_re = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]
_pii_re = {name: re.compile(p) for name, p in _PII_PATTERNS.items()}


def detect_prompt_injection(text: str) -> str | None:
    for pattern in _injection_re:
        if pattern.search(text):
            return pattern.pattern
    return None


def detect_pii(text: str) -> list[str]:
    return [name for name, pattern in _pii_re.items() if pattern.search(text)]


def redact_pii(text: str) -> str:
    redacted = text
    for name, pattern in _pii_re.items():
        redacted = pattern.sub(f"[REDACTED_{name.upper()}]", redacted)
    return redacted


def check_input(text: str) -> tuple[bool, str]:
    """Return (allowed, reason). Blocks on prompt injection only; PII is redacted, not blocked."""
    injection = detect_prompt_injection(text)
    if injection:
        return False, f"Potential prompt injection detected (pattern: {injection})"
    return True, ""


def check_output(answer: str, contexts: list[str]) -> list[str]:
    """Cheap hallucination indicators to surface in traces (non-blocking)."""
    warnings = []
    if not contexts:
        warnings.append("no_context_used")
    if not answer.strip():
        warnings.append("empty_answer")
    return warnings
