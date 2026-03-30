from __future__ import annotations

import re
from typing import Dict, List

from rapidfuzz import fuzz, process


HINGLISH_MAP = {
    "kabja": "encroachment",
    "zameen": "land",
    "jameen": "land",
    "paisa": "money",
    "dhokha": "fraud",
    "thagi": "scam",
    "thag": "scam",
    "thana": "police station",
    "salary nahi mila": "salary not paid",
    "naukri se nikal": "job termination",
    "online paisa gaya": "online fraud",
    "upi se chala gaya": "upi fraud",
    "kabza": "encroachment",
    "maar peet": "assault",
    "maarpit": "assault",
    "ghar se nikala": "domestic violence",
    "biwi pati jhagda": "family dispute",
    "cheated": "fraud",
    "cheat": "fraud",
}

SYNONYMS = {
    "scam": ["fraud", "cyber crime"],
    "scammed": ["fraud", "cyber fraud", "cyber crime"],
    "fraud": ["cheating", "cyber crime"],
    "cheated": ["fraud", "cyber fraud", "cheating"],
    "cheating": ["fraud", "cyber fraud"],
    "upi": ["online payment", "digital payment", "cyber fraud"],
    "online": ["internet", "cyber"],
    "land": ["property", "land dispute"],
    "encroachment": ["illegal occupation", "land dispute"],
    "salary": ["wage", "salary non-payment"],
    "termination": ["job loss", "wrongful termination"],
    "assault": ["violence", "police complaint"],
    "domestic": ["family", "domestic violence"],
    "property": ["land", "land dispute"],
}

INTENT_KEYWORDS = {
    "cyber_fraud": [
        "upi",
        "fraud",
        "cheated",
        "cheating",
        "scam",
        "cyber",
        "otp",
        "online payment",
        "digital payment",
        "money",
    ],
    "land_dispute": [
        "land",
        "encroachment",
        "property",
        "boundary",
        "kabja",
        "land dispute",
    ],
    "labour_issue": [
        "salary",
        "wage",
        "employer",
        "termination",
        "job",
        "salary non-payment",
    ],
    "police_complaint": [
        "assault",
        "threat",
        "harassment",
        "police",
        "fir",
        "violence",
    ],
    "family_issue": [
        "divorce",
        "maintenance",
        "custody",
        "family",
        "domestic violence",
        "marriage",
    ],
}

STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "to",
    "for",
    "of",
    "in",
    "on",
    "my",
    "me",
    "mera",
    "meri",
    "mujhe",
    "ko",
    "ne",
    "ki",
    "ka",
    "ke",
    "ho",
    "gaya",
    "gayi",
    "hai",
    "someone",
    "through",
    "by",
    "with",
    "se",
    "par",
    "nahi",
    "mila",
    "chala",
}

CANONICAL_TERMS = sorted(
    set(
        list(HINGLISH_MAP.values())
        + list(SYNONYMS.keys())
        + [item for values in SYNONYMS.values() for item in values]
        + ["fraud", "cyber", "crime", "upi", "land", "salary", "encroachment", "dispute"]
    )
)


def _normalize_hinglish(text: str) -> str:
    normalized = text
    for src, target in HINGLISH_MAP.items():
        normalized = re.sub(rf"\b{re.escape(src)}\b", target, normalized)
    return normalized


def _clean_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = _normalize_hinglish(text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _correct_token(token: str) -> str:
    if token.isdigit() or len(token) <= 2:
        return token

    best = process.extractOne(token, CANONICAL_TERMS, scorer=fuzz.WRatio)
    if not best:
        return token

    candidate, score, _ = best
    if score >= 80:
        return candidate
    return token


def _tokenize(text: str) -> List[str]:
    tokens = [t for t in text.split() if t and t not in STOPWORDS]
    corrected = [_correct_token(token) for token in tokens]
    return corrected


def _unique_preserve(items: List[str]) -> List[str]:
    seen = set()
    output = []
    for item in items:
        token = item.strip()
        if not token or token in seen:
            continue
        seen.add(token)
        output.append(token)
    return output


def _expand_synonyms(tokens: List[str]) -> List[str]:
    expanded = []
    for token in tokens:
        expanded.append(token)
        for synonym in SYNONYMS.get(token, []):
            expanded.append(synonym)
    return _unique_preserve(expanded)


def _detect_intent(expanded: List[str]) -> str:
    query_blob = " ".join(expanded)
    best_intent = "general_legal"
    best_score = 0

    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in query_blob)
        if score > best_score:
            best_score = score
            best_intent = intent

    return best_intent


def _classify_query(intent: str, expanded: List[str]) -> str:
    if intent == "general_legal":
        if any(term in expanded for term in ["urgent", "immediate", "help"]):
            return "general_urgent"
        return "general_information"

    if any(term in expanded for term in ["what", "how", "know", "advice"]):
        return "advisory"

    if any(term in expanded for term in ["complaint", "fir", "report", "case"]):
        return "actionable_complaint"

    return "actionable_guidance"


def process_query(query: str) -> Dict:
    text = "" if query is None else str(query)
    cleaned = _clean_text(text)
    tokens = _tokenize(cleaned)
    expanded = _expand_synonyms(tokens)
    intent = _detect_intent(expanded)
    query_type = _classify_query(intent, expanded)

    return {
        "normalized": cleaned,
        "tokens": tokens,
        "expanded": expanded,
        "expanded_text": " ".join(expanded),
        "intent": intent,
        "query_type": query_type,
    }
