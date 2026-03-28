"""Multilingual query understanding for NyaySaathi.

Pipeline:
User Input -> Cleaning -> Hinglish Normalization -> Tokenization -> Synonym Expansion
-> Intent-oriented Query Expansion -> Semantic Search Ready Query + Confidence Signals
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate

    _HAS_INDIC_TRANSLITERATION = True
except Exception:  # noqa: BLE001
    _HAS_INDIC_TRANSLITERATION = False


NOISE_WORDS = {
    "please",
    "plz",
    "help",
    "urgent",
    "sir",
    "madam",
    "kindly",
    "issue",
    "problem",
    "mera",
    "meri",
    "mere",
    "mujhe",
    "mujhko",
    "majha",
    "mazi",
    "माझा",
    "माझी",
    "माझे",
    "मेरा",
    "मेरी",
    "मुझे",
    "hai",
    "haii",
    "ho",
    "hoga",
    "raha",
    "rahi",
    "rahe",
    "rahey",
    "karta",
    "karte",
    "karti",
    "kar",
    "kare",
    "karo",
    "karna",
    "ka",
    "ki",
    "ke",
    "kya",
}

LEGAL_CANONICAL_VARIANTS: Dict[str, set[str]] = {
    "salary": {"salary", "salry", "sallary", "vetan", "pagar", "तनख्वाह", "वेतन", "पगार"},
    "employer": {"employer", "company", "boss", "malik", "naukriwala", "नियोक्ता", "मालिक", "कंपनी", "मालक"},
    "not": {"not", "nahi", "nai", "nhi", "nahin", "nahii", "नहीं", "नही", "नहि", "नाही"},
    "paid": {"paid", "mila", "milaa", "milala", "मिला", "मिळाला", "मिळाले", "दिया", "दिल्या"},
    "complaint": {"complaint", "compaint", "complent", "shikayat", "तक्रार", "शिकायत", "fir"},
    "fir": {"fir", "एफआईआर", "एफिर", "एफआयआर"},
    "police": {"police", "polis", "polce", "thanedar", "thana", "पुलिस", "पोलीस", "थाना"},
    "fraud": {"fraud", "fruad", "scam", "dhokha", "thagi", "फ्रॉड", "धोखा", "ठगी"},
    "upi": {"upi", "gpay", "phonepe", "paytm", "यूपीआई"},
    "landlord": {"landlord", "ghar malik", "makan malik", "मकान मालिक", "घरमालक", "मालक"},
    "tenant": {"tenant", "kirayedar", "भाडेकरू", "किरायेदार"},
    "rent": {"rent", "kiraya", "bhada", "भाड़ा", "किराया", "भाडे"},
    "deposit": {"deposit", "security", "advance", "thev", "डिपॉजिट", "ठेव", "जमा"},
    "return": {"return", "wapas", "parat", "परत", "वापस"},
    "land": {"land", "zameen", "jameen", "jamin", "भूमि", "जमीन", "जमिन"},
    "property": {"property", "makan", "मकान", "मालमत्ता"},
    "violence": {
        "violence",
        "maar",
        "marpeet",
        "jhagda",
        "jagda",
        "ghar",
        "home",
        "भांडण",
        "झगड़ा",
        "झगडा",
        "मारपीट",
        "मारहाण",
        "abuse",
        "harassment",
        "उत्पीड़न",
        "छळ",
    },
    "dowry": {"dowry", "dahej", "हुंडा", "दहेज"},
    "divorce": {"divorce", "talak", "तलाक", "घटस्फोट"},
    "scheme": {"scheme", "yojana", "योजना", "स्कीम"},
    "pension": {"pension", "पेंशन", "पेन्शन"},
    "consumer": {"consumer", "defective", "refund", "warranty", "ग्राहक", "रिफंड"},
    "document": {"document", "certificate", "दस्तावेज", "प्रमाणपत्र"},
}

LEGAL_SYNONYM_EXPANSION: Dict[str, List[str]] = {
    "complaint": ["complaint", "fir", "legal complaint", "police complaint"],
    "fir": ["fir", "police complaint", "crime report"],
    "salary": ["salary", "wage", "labour payment", "employment dispute"],
    "fraud": ["fraud", "cyber crime", "financial scam", "bank complaint"],
    "upi": ["upi fraud", "digital payment fraud", "cyber complaint"],
    "landlord": ["landlord", "tenant dispute", "rental dispute"],
    "deposit": ["security deposit", "rent deposit", "tenant rights"],
    "property": ["property dispute", "land records", "civil dispute"],
    "violence": ["domestic violence", "protection order", "women safety"],
    "consumer": ["consumer complaint", "consumer forum", "refund claim"],
    "scheme": ["government scheme", "benefit eligibility", "public service"],
}

SHORT_QUERY_EXPANSION: Dict[str, str] = {
    "salary": "salary not paid by employer",
    "fir": "police refusing to register fir",
    "deposit": "security deposit not returned by landlord",
    "upi": "upi payment fraud cyber complaint",
    "pension": "pension benefit delay and grievance",
}

_FALLBACK_DEVANAGARI_ROMAN_MAP: Dict[str, str] = {
    "पुलिस": "police",
    "पोलीस": "police",
    "तक्रार": "complaint",
    "शिकायत": "complaint",
    "वेतन": "salary",
    "तनख्वाह": "salary",
    "पगार": "salary",
    "नहीं": "not",
    "नाही": "not",
    "मिळाला": "received",
    "मिळाले": "received",
    "मकान": "house",
    "घर": "house",
    "जमीन": "land",
    "ठगी": "fraud",
    "धोखा": "fraud",
    "डिपॉजिट": "deposit",
}


def _basic_normalize(text: str) -> str:
    cleaned = str(text or "").lower().strip()
    cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
    cleaned = re.sub(r"[^\w\s\u0900-\u097F]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


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
            for src, tgt in zip(list(hi.get("descriptions") or []), list(en.get("descriptions") or [])):
                _add_phrase_map(mapping, str(src), str(tgt))

    if mr_rows and len(mr_rows) == len(en_rows):
        for en, mr in zip(en_rows, mr_rows):
            for key in ("category", "subcategory", "problem_description"):
                _add_phrase_map(mapping, str(mr.get(key, "")), str(en.get(key, "")))
            for src, tgt in zip(list(mr.get("descriptions") or []), list(en.get("descriptions") or [])):
                _add_phrase_map(mapping, str(src), str(tgt))

    logger.info("Loaded %d dataset phrase mappings for multilingual query normalization", len(mapping))
    return mapping


DATASET_PHRASE_MAP = _build_dataset_phrase_map()


def _build_variant_index() -> Tuple[Dict[str, str], List[str], Dict[str, str]]:
    variant_to_canonical: Dict[str, str] = {}
    fuzzy_vocab: List[str] = []
    phonetic_map: Dict[str, str] = {}

    for canonical, variants in LEGAL_CANONICAL_VARIANTS.items():
        all_forms = set(variants)
        all_forms.add(canonical)
        for form in all_forms:
            norm = _basic_normalize(form)
            if not norm:
                continue
            variant_to_canonical[norm] = canonical
            fuzzy_vocab.append(norm)
            key = _phonetic_key(norm)
            if key and key not in phonetic_map:
                phonetic_map[key] = canonical

    return variant_to_canonical, sorted(set(fuzzy_vocab)), phonetic_map


def _phonetic_key(token: str) -> str:
    value = re.sub(r"[^a-z]", "", token.lower())
    if not value:
        return ""

    replacements = (
        ("ph", "f"),
        ("bh", "b"),
        ("kh", "k"),
        ("gh", "g"),
        ("ch", "c"),
        ("sh", "s"),
        ("th", "t"),
        ("dh", "d"),
    )
    for old, new in replacements:
        value = value.replace(old, new)

    value = re.sub(r"(.)\1+", r"\1", value)
    return value[:1] + re.sub(r"[aeiou]", "", value[1:])


_VARIANT_TO_CANONICAL, _FUZZY_VOCAB, _PHONETIC_MAP = _build_variant_index()


@dataclass
class ProcessedQuery:
    raw_query: str
    language: str
    cleaned: str
    transliterated: str
    normalized: str
    translated: str
    expanded: str
    keywords: List[str]
    tokens: List[str]
    expanded_terms: List[str]
    ambiguity_score: float
    confidence_hint: str
    debug_signals: Dict[str, float]


def detect_language(text: str) -> str:
    """Detect broad language class: English, Hindi, Marathi, or Mixed."""
    value = str(text or "")
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", value))
    has_latin = bool(re.search(r"[A-Za-z]", value))

    if has_devanagari and has_latin:
        return "Mixed"
    if has_devanagari:
        marathi_markers = ("मिळ", "आहे", "नाही", "भाडे", "पोलीस", "तक्रार")
        if any(m in value for m in marathi_markers):
            return "Marathi"
        return "Hindi"

    lowered = value.lower()
    if re.search(r"\b(mera|nahi|paise|kiraya|majha|milala|kase|kaise)\b", lowered):
        return "Mixed"
    return "English"


def normalize_text(text: str) -> str:
    return _basic_normalize(text)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z\u0900-\u097F0-9]+", text.lower())


def _transliterate_token(token: str) -> str:
    if not re.search(r"[\u0900-\u097F]", token):
        return token

    if _HAS_INDIC_TRANSLITERATION:
        try:
            roman = transliterate(token, sanscript.DEVANAGARI, sanscript.ITRANS)
            roman = _basic_normalize(roman)
            if roman:
                return roman
        except Exception:  # noqa: BLE001
            pass

    return _FALLBACK_DEVANAGARI_ROMAN_MAP.get(token, token)


def _normalize_token(token: str) -> Tuple[str, bool]:
    base = _basic_normalize(token)
    if not base:
        return "", False

    if base in NOISE_WORDS:
        return "", False

    mapped = _VARIANT_TO_CANONICAL.get(base)
    if mapped:
        return mapped, True

    transliterated = _transliterate_token(base)
    if transliterated != base:
        mapped = _VARIANT_TO_CANONICAL.get(transliterated)
        if mapped:
            return mapped, True

    key = _phonetic_key(transliterated)
    if key in _PHONETIC_MAP:
        return _PHONETIC_MAP[key], True

    if len(transliterated) >= 3:
        cutoff = 90 if len(transliterated) <= 4 else 84
        best = process.extractOne(transliterated, _FUZZY_VOCAB, scorer=fuzz.WRatio, score_cutoff=cutoff)
        if best:
            canonical = _VARIANT_TO_CANONICAL.get(best[0])
            if canonical:
                return canonical, True

    if transliterated in {"kese", "kaisey", "kaise", "kase", "kaisa", "kaisi"}:
        return "how", True
    return transliterated, False


def _apply_dataset_phrase_map(text: str) -> str:
    value = text
    for source, target in sorted(DATASET_PHRASE_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        if source in value:
            value = value.replace(source, target)
    return value


def _expand_terms(tokens: List[str]) -> List[str]:
    expanded: List[str] = []
    seen = set()
    for token in tokens:
        if not token or token in NOISE_WORDS:
            continue
        if token not in seen:
            expanded.append(token)
            seen.add(token)

        for synonym in LEGAL_SYNONYM_EXPANSION.get(token, []):
            item = _basic_normalize(synonym)
            if item and item not in seen:
                expanded.append(item)
                seen.add(item)
    return expanded


def _intent_expand(tokens: List[str], expanded_terms: List[str], base_text: str) -> str:
    token_set = set(tokens)
    phrase = base_text

    if {"salary", "employer"}.intersection(token_set) and ("not" in token_set or "paid" in token_set):
        phrase = f"salary not paid by employer labour wage dispute {phrase}".strip()
    elif ({"police", "fir"}.intersection(token_set) and "not" in token_set) or (
        "police" in token_set and "complaint" in token_set
    ):
        phrase = f"police refusing to register fir complaint inaction {phrase}".strip()
    elif ({"upi", "fraud"}.issubset(token_set)) or ({"upi", "fraud"}.intersection(token_set) == {"fraud"}):
        phrase = f"upi payment fraud cyber crime bank complaint {phrase}".strip()
    elif {"landlord", "tenant", "deposit"}.intersection(token_set) and (
        "return" in token_set or "not" in token_set
    ):
        phrase = f"landlord tenant security deposit not returned tenancy dispute {phrase}".strip()
    elif "violence" in token_set:
        phrase = f"domestic violence family protection legal remedy {phrase}".strip()
    elif {"property", "land"}.intersection(token_set):
        phrase = f"property land civil dispute records ownership issue {phrase}".strip()

    if len(tokens) <= 3:
        for token in tokens:
            if token in SHORT_QUERY_EXPANSION:
                phrase = f"{SHORT_QUERY_EXPANSION[token]} {phrase}".strip()

    if expanded_terms:
        phrase = f"{phrase} {' '.join(expanded_terms[:16])}".strip()
    return re.sub(r"\s+", " ", phrase).strip()


def _extract_keywords(tokens: List[str], expanded_terms: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for token in tokens + expanded_terms:
        if len(token) < 3 or token in NOISE_WORDS:
            continue
        if token not in seen:
            out.append(token)
            seen.add(token)
    return out[:14]


def _estimate_ambiguity(tokens: List[str], recognized: int, keywords: List[str], expanded_text: str) -> Tuple[float, Dict[str, float]]:
    total_tokens = max(1, len(tokens))
    recognized_ratio = min(1.0, recognized / total_tokens)

    legal_anchor_terms = {
        "salary",
        "employer",
        "police",
        "fir",
        "fraud",
        "upi",
        "landlord",
        "tenant",
        "deposit",
        "property",
        "consumer",
        "violence",
        "scheme",
        "pension",
    }
    anchor_count = sum(1 for token in tokens if token in legal_anchor_terms)
    anchor_ratio = min(1.0, anchor_count / 2.0)
    keyword_depth = min(1.0, len(keywords) / 8.0)

    ambiguity_signals = (0.45 * (1.0 - recognized_ratio)) + (0.35 * (1.0 - anchor_ratio)) + (0.20 * (1.0 - keyword_depth))
    ambiguity = max(0.0, min(1.0, ambiguity_signals))

    if len(expanded_text.split()) <= 2:
        ambiguity = min(1.0, ambiguity + 0.20)

    debug = {
        "recognized_ratio": round(recognized_ratio, 4),
        "anchor_ratio": round(anchor_ratio, 4),
        "keyword_depth": round(keyword_depth, 4),
        "ambiguity_score": round(ambiguity, 4),
    }
    return ambiguity, debug


def _confidence_hint_from_ambiguity(ambiguity: float) -> str:
    if ambiguity <= 0.32:
        return "High"
    if ambiguity <= 0.58:
        return "Medium"
    return "Low"


def process_query(raw_query: str) -> ProcessedQuery:
    """Run multilingual NLP understanding for semantic retrieval."""
    text = str(raw_query or "").strip()
    if not text:
        return ProcessedQuery(
            raw_query="",
            language="Unknown",
            cleaned="",
            transliterated="",
            normalized="",
            translated="",
            expanded="",
            keywords=[],
            tokens=[],
            expanded_terms=[],
            ambiguity_score=1.0,
            confidence_hint="Low",
            debug_signals={"recognized_ratio": 0.0, "anchor_ratio": 0.0, "keyword_depth": 0.0, "ambiguity_score": 1.0},
        )

    language = detect_language(text)
    cleaned = normalize_text(text)
    cleaned = _apply_dataset_phrase_map(cleaned)

    raw_tokens = _tokenize(cleaned)
    normalized_tokens: List[str] = []
    transliterated_tokens: List[str] = []
    recognized = 0

    for token in raw_tokens:
        roman = _transliterate_token(token)
        transliterated_tokens.append(roman)
        normalized, ok = _normalize_token(token)
        if normalized:
            normalized_tokens.append(normalized)
        if ok:
            recognized += 1

    expanded_terms = _expand_terms(normalized_tokens)
    translated = " ".join(normalized_tokens).strip()
    expanded = _intent_expand(normalized_tokens, expanded_terms, translated)
    keywords = _extract_keywords(normalized_tokens, expanded_terms)

    ambiguity, debug_signals = _estimate_ambiguity(normalized_tokens, recognized, keywords, expanded)
    confidence_hint = _confidence_hint_from_ambiguity(ambiguity)

    logger.debug(
        "Processed query lang=%s cleaned=%r normalized=%r expanded=%r ambiguity=%.3f",
        language,
        cleaned,
        translated,
        expanded,
        ambiguity,
    )

    return ProcessedQuery(
        raw_query=text,
        language=language,
        cleaned=cleaned,
        transliterated=" ".join(transliterated_tokens).strip(),
        normalized=translated,
        translated=translated,
        expanded=expanded,
        keywords=keywords,
        tokens=normalized_tokens,
        expanded_terms=expanded_terms,
        ambiguity_score=round(float(ambiguity), 4),
        confidence_hint=confidence_hint,
        debug_signals=debug_signals,
    )
