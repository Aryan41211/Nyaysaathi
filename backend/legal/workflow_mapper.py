"""Workflow mapping for category-driven legal guidance responses."""

from __future__ import annotations

from typing import Final

WORKFLOWS: Final[dict[str, list[str]]] = {
    "LABOUR": [
        "Talk to employer and request payment.",
        "Send written complaint email to HR or management.",
        "Collect salary slips, contract, and payment proof.",
        "Contact Labour Commissioner office in your district.",
        "File complaint on official labour grievance portal.",
    ],
    "CYBER": [
        "Report incident at cybercrime.gov.in immediately.",
        "Call 1930 cyber helpline and register complaint.",
        "Inform your bank and block risky transactions.",
        "Freeze affected accounts/cards and reset credentials.",
        "Preserve screenshots, transaction IDs, and messages.",
    ],
    "PROPERTY": [
        "Send written notice to landlord or opposite party.",
        "Collect agreement, rent receipts, and communication records.",
        "Approach local rent authority or housing grievance cell.",
        "Seek legal notice through advocate if unresolved.",
        "File civil complaint before competent court if needed.",
    ],
}

CLARIFICATION_QUESTIONS: Final[dict[str, list[str]]] = {
    "LABOUR": [
        "Is this related to unpaid salary or pending wages?",
        "Is this related to an employment dispute with your employer?",
    ],
    "CYBER": [
        "Did this involve online fraud, UPI, or bank account misuse?",
        "Was your account hacked or money transferred without consent?",
    ],
    "PROPERTY": [
        "Is this about landlord-tenant rent or deposit dispute?",
        "Is this about property ownership, possession, or refund conflict?",
    ],
}

DEFAULT_WORKFLOW: Final[list[str]] = ["Please describe problem more clearly."]


def get_workflow(category: str) -> list[str]:
    """Return workflow steps for a detected category."""
    normalized = str(category or "").strip().upper()
    return list(WORKFLOWS.get(normalized, DEFAULT_WORKFLOW))


def get_clarification_questions(category: str) -> list[str]:
    """Return two category-based clarification prompts."""
    normalized = str(category or "").strip().upper()
    return list(
        CLARIFICATION_QUESTIONS.get(
            normalized,
            [
                "Can you share more details about the legal issue?",
                "Who is involved and what outcome do you want?",
            ],
        )
    )


def build_explanation(category: str, matched_text: str) -> str:
    """Create user-facing explanation for classification transparency."""
    normalized = str(category or "Unknown").strip().upper()
    anchor = str(matched_text or "similar legal complaints").strip()
    return (
        f"This issue is classified as {normalized} because it closely matches "
        f"{anchor}."
    )
