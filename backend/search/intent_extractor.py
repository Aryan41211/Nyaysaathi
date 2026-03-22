"""Intent and authority extraction for NyaySaathi search."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


INTENT_RULES: List[Tuple[str, str, str, str, str]] = [
    (r"salary|wage|employer|labour|payment not paid", "Employment issue", "Labour and Wage Issues", "Salary/Wage Dispute", "Employer"),
    (r"upi|fraud|cyber|scam|phishing", "Cyber fraud", "Cyber Fraud and Digital Scams", "Digital Fraud", "Bank"),
    (r"police|fir|complaint refusal", "Police issue", "Police Complaints and Local Crime", "Police Inaction", "Police"),
    (r"defective|consumer|refund|warranty", "Consumer dispute", "Consumer Complaints", "Consumer Grievance", "Consumer Forum"),
    (r"land|property|encroach|registry|tenant|landlord|deposit|rent", "Property issue", "Land and Property Disputes", "Property/Tenancy Dispute", "Court"),
    (r"domestic violence|husband|wife|family|harassment", "Family issue", "Domestic Violence and Family Disputes", "Family Protection", "Court"),
    (r"municipal|garbage|pollution|noise|nuisance", "Public nuisance", "Environmental and Public Nuisance Complaints", "Public Nuisance", "Municipality"),
]


@dataclass
class IntentInfo:
    matched_intent: str
    legal_domain: str
    problem_type: str
    authority_type: str


def extract_intent(text: str) -> IntentInfo:
    """Extract high-level legal intent/domain/authority from processed query text."""
    for pattern, intent, domain, ptype, authority in INTENT_RULES:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return IntentInfo(
                matched_intent=intent,
                legal_domain=domain,
                problem_type=ptype,
                authority_type=authority,
            )

    return IntentInfo(
        matched_intent="General legal issue",
        legal_domain="Unknown",
        problem_type="General",
        authority_type="Court",
    )
