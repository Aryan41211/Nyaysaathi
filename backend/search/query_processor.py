"""Query preprocessing for NyaySaathi semantic search.

Handles normalization, multilingual tolerance (English/Hindi/Marathi/Mixed),
spell correction, noise removal, and short-query intent expansion.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def _basic_normalize(text: str) -> str:
    cleaned = str(text or "").lower().strip()
    cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
    cleaned = re.sub(r"[^\w\s\u0900-\u097F]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

NOISE_WORDS = {
    "please", "plz", "help", "urgent", "sir", "madam", "kindly", "issue", "problem",
    "mera", "meri", "majha", "mazi", "hai", "ho", "hoga", "kar", "karo",
}

SPELL_FIXES = {
    "salry": "salary",
    "sallary": "salary",
    "pagar": "salary",
    "vetan": "salary",
    "landlrod": "landlord",
    "depositt": "deposit",
    "retun": "return",
    "compaint": "complaint",
    "fruad": "fraud",
    "polce": "police",
    "goverment": "government",
}

TRANSLATION_PATTERNS: Dict[str, str] = {
    r"\bnahi\b|\bnai\b|\bnahin\b|\bnaahi\b": "not",
    r"नाही": "not",
    r"नहीं|नही|नहि": "not",
    r"\bpolis\b|\bpolice\b": "police",
    r"पुलिस": "police",
    r"\bpaisa\b|\bpaise\b|\brakkam\b": "money",
    r"पैसा|पैसे|रकम": "money",
    r"\bboss\b|\bmalik\b|\bcompany\b": "employer",
    r"मालक": "landlord",
    r"नियोक्ता|मालिक|कंपनी|कम्पनी": "employer",
    r"वेतन|तनख्वाह|पगार": "salary",
    r"नहीं\s+दिया|नहीं\s+मिला|नाही\s+मिळाला|नाही\s+मिळाले|मिळाला\s+नाही|मिळाले\s+नाही": "not paid",
    r"\bkiraya\b|\bbhada\b": "rent",
    r"किराया|भाड़ा": "rent",
    r"\bmakaan\b|\bmakan\b|\bghar\b": "house",
    r"मकान|घर": "house",
    r"\bzameen\b|\bzamin\b|\bjamin\b|\bmalmatta\b": "land",
    r"जमीन|भूमि": "land",
    r"\bmakan malik\b|\bghar malik\b": "landlord",
    r"\badvance\b|\bthev\b": "deposit",
    r"डिपॉझिट|डिपॉजिट|ठेव": "deposit",
    r"\bparat\b|\bwapas\b": "return",
    r"परत": "return",
    r"\btakrar\b ghet nahi|\bfir\b nahi|\bfir\b ghet nahi|\bcomplaint\b nahi leti": "police fir refusal",
    r"\bdhokha\b|\bthagi\b": "fraud",
    r"धोखा|ठगी|फ्रॉड": "fraud",
}

SHORT_EXPANSION = {
    "salary": "salary not paid by employer",
    "deposit": "security deposit not returned by landlord",
    "fir": "police refusing to register fir",
    "upi": "upi payment fraud cyber complaint",
}


def _load_dataset_rows(path: Path) -> List[dict]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, list):
            return [r for r in raw if isinstance(r, dict)]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load dataset translation source %s: %s", path, exc)
    return []


def _add_phrase_map(mapping: Dict[str, str], source: str, target: str) -> None:
    src = _basic_normalize(source)
    tgt = _basic_normalize(target)
    if not src or not tgt or src == tgt:
        return
    # Prefer longer/clearer targets if duplicate source appears.
    existing = mapping.get(src)
    if existing and len(existing) >= len(tgt):
        return
    mapping[src] = tgt


def _build_dataset_phrase_map() -> Dict[str, str]:
    backend_dir = Path(__file__).resolve().parents[1]
    repo_dir = backend_dir.parent

    en_candidates = [
        backend_dir / "data" / "nyaysaathi_en.json",
        repo_dir / "dataset" / "legal_cases.json",
    ]
    hi_candidates = [
        backend_dir / "data" / "nyaysaathi_hi.json",
        repo_dir / "nyaysaathi_hindi.json",
    ]
    mr_candidates = [
        backend_dir / "data" / "nyaysaathi_mr.json",
        repo_dir / "nyaysaathi_marathi.json",
    ]

    en_rows: List[dict] = []
    hi_rows: List[dict] = []
    mr_rows: List[dict] = []

    for p in en_candidates:
        en_rows = _load_dataset_rows(p)
        if en_rows:
            break
    for p in hi_candidates:
        hi_rows = _load_dataset_rows(p)
        if hi_rows:
            break
    for p in mr_candidates:
        mr_rows = _load_dataset_rows(p)
        if mr_rows:
            break

    mapping: Dict[str, str] = {}
    if not en_rows:
        return mapping

    if hi_rows and len(hi_rows) == len(en_rows):
        for en, hi in zip(en_rows, hi_rows):
            for key in ("category", "subcategory", "problem_description"):
                _add_phrase_map(mapping, str(hi.get(key, "")), str(en.get(key, "")))
            hi_desc = list(hi.get("descriptions") or [])
            en_desc = list(en.get("descriptions") or [])
            for src, tgt in zip(hi_desc, en_desc):
                _add_phrase_map(mapping, str(src), str(tgt))

    if mr_rows and len(mr_rows) == len(en_rows):
        for en, mr in zip(en_rows, mr_rows):
            for key in ("category", "subcategory", "problem_description"):
                _add_phrase_map(mapping, str(mr.get(key, "")), str(en.get(key, "")))
            mr_desc = list(mr.get("descriptions") or [])
            en_desc = list(en.get("descriptions") or [])
            for src, tgt in zip(mr_desc, en_desc):
                _add_phrase_map(mapping, str(src), str(tgt))

    logger.info("Loaded %d dataset phrase mappings for multilingual query normalization", len(mapping))
    return mapping


DATASET_PHRASE_MAP = _build_dataset_phrase_map()


@dataclass
class ProcessedQuery:
    raw_query: str
    language: str
    normalized: str
    translated: str
    expanded: str
    keywords: List[str]


def detect_language(text: str) -> str:
    """Detect broad language class: English, Hindi, Marathi, or Mixed."""
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", text))
    has_latin = bool(re.search(r"[A-Za-z]", text))

    if has_devanagari and has_latin:
        return "Mixed"
    if has_devanagari:
        marathi_markers = ["nahi", "aahe", "majha", "milala", "माझा", "माझे", "आहे", "नाही", "मिळाला", "मिळाले"]
        lowered = text.lower()
        if any(m in lowered for m in marathi_markers):
            return "Marathi"
        return "Hindi"
    if re.search(r"\b(mera|nahi|paisa|kiraya|ghar|zamin|malik|majha|milala)\b", text.lower()):
        return "Mixed"
    return "English"


def normalize_text(text: str) -> str:
    """Lowercase and remove punctuation/extra spaces while preserving unicode letters."""
    return _basic_normalize(text)


def _translate_lightweight(text: str) -> str:
    translated = text
    for pattern, replacement in TRANSLATION_PATTERNS.items():
        translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)

    if DATASET_PHRASE_MAP:
        # Replace longer phrases first to avoid partial replacement conflicts.
        for source, target in sorted(DATASET_PHRASE_MAP.items(), key=lambda item: len(item[0]), reverse=True):
            if source in translated:
                translated = translated.replace(source, target)

    return translated


def _correct_spelling(text: str) -> str:
    tokens = []
    for token in text.split():
        tokens.append(SPELL_FIXES.get(token, token))
    return " ".join(tokens)


def _remove_noise(text: str) -> str:
    return " ".join(t for t in text.split() if t not in NOISE_WORDS)


def _expand_short_query(text: str) -> str:
    tokens = text.split()
    if len(tokens) <= 3:
        for t in tokens:
            if t in SHORT_EXPANSION:
                return f"{SHORT_EXPANSION[t]} {text}".strip()
    return text


def _intent_expand(text: str) -> str:
    """Expand common legal intents into canonical English query phrases."""
    t = text

    if re.search(r"(salary|wage|money).*(not|unpaid|due)| (not|unpaid).*(salary|wage|money)", t):
        return f"salary not paid by employer labour wage dispute {t}".strip()

    if re.search(r"(landlord|tenant|house).*(deposit|advance|security).*(not|return)| (deposit|advance).*(not|return)", t):
        return f"landlord refusing to return security deposit tenancy dispute {t}".strip()

    if re.search(r"police.*fir.*(not|refusal)|fir.*(not|refusal)|complaint refusal", t):
        return f"police refusing to register fir police complaint inaction {t}".strip()

    if re.search(r"upi|online payment|digital payment", t) and re.search(r"fraud|scam|thagi|dhokha", t):
        return f"upi payment fraud cyber crime bank complaint {t}".strip()

    return t


def _extract_keywords(text: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for tok in text.split():
        if len(tok) < 3:
            continue
        if tok in NOISE_WORDS:
            continue
        if tok not in seen:
            out.append(tok)
            seen.add(tok)
    return out[:10]


def process_query(raw_query: str) -> ProcessedQuery:
    """Run the full query-understanding pipeline and return structured output."""
    normalized = normalize_text(raw_query)
    translated = _translate_lightweight(normalized)
    translated = _correct_spelling(translated)
    translated = _remove_noise(translated)
    expanded = _expand_short_query(translated)
    expanded = _intent_expand(expanded)

    language = detect_language(raw_query)
    keywords = _extract_keywords(expanded)

    logger.debug("Processed query lang=%s normalized=%r expanded=%r", language, normalized, expanded)

    return ProcessedQuery(
        raw_query=raw_query,
        language=language,
        normalized=normalized,
        translated=translated,
        expanded=expanded,
        keywords=keywords,
    )
