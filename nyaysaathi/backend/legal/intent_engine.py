"""Intent categorization rules for local legal understanding output."""

from __future__ import annotations

QUESTION_HINTS = ("what", "how", "when", "where", "why", "can", "should", "?")
COMPLAINT_HINTS = (
    "not",
    "fraud",
    "hacked",
    "scam",
    "refusing",
    "delayed",
    "pending",
    "issue",
    "complaint",
)


class IntentEngine:
    """Resolve high-level intent label from user text."""

    @staticmethod
    def detect_intent(user_input: str) -> str:
        text = (user_input or "").lower().strip()
        if not text:
            return "guidance"

        if any(token in text for token in QUESTION_HINTS):
            return "information"

        if any(token in text for token in COMPLAINT_HINTS):
            return "complaint"

        return "guidance"
