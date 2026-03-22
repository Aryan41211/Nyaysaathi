"""Multilingual workflow retrieval service backed by MongoDB.

Collection schema (preferred Option A):
{
  "category_id": "salary_not_paid_by_employer",
  "translations": {
    "en": {...},
    "hi": {...},
    "mr": {...}
  },
  "search_aliases": {
    "en": ["labour and wage issues", "salary not paid by employer"],
    "hi": ["..."],
    "mr": ["..."]
  }
}
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any

from rapidfuzz import fuzz

from config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from legal_cases.db_connection import get_collection

logger = logging.getLogger(__name__)

_WORKFLOW_COLL = "legal_workflows_multilingual"
_CACHE_TTL_SECONDS = 300

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {
    "expires_at": 0.0,
    "docs": {},
    "alias_to_id": {},
    "all_aliases": [],
}

_SPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s\u0900-\u097F]")


def _normalize_text(value: str | None) -> str:
    text = str(value or "").strip().lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text


def _normalize_language(language: str | None) -> str:
    lang = (language or "").strip().lower()
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return DEFAULT_LANGUAGE


def _create_indexes() -> None:
    col = get_collection(_WORKFLOW_COLL)
    col.create_index("category_id", unique=True)
    col.create_index("translations.en.category")
    col.create_index("translations.en.subcategory")
    col.create_index("translations.hi.category")
    col.create_index("translations.hi.subcategory")
    col.create_index("translations.mr.category")
    col.create_index("translations.mr.subcategory")


def _load_cache() -> dict[str, Any]:
    now = time.time()
    with _CACHE_LOCK:
        if _CACHE["docs"] and _CACHE["expires_at"] > now:
            return {
                "docs": dict(_CACHE["docs"]),
                "alias_to_id": dict(_CACHE["alias_to_id"]),
                "all_aliases": list(_CACHE["all_aliases"]),
            }

    _create_indexes()
    docs = list(get_collection(_WORKFLOW_COLL).find({}, {"_id": 0}))

    by_id: dict[str, dict[str, Any]] = {}
    alias_to_id: dict[str, str] = {}
    all_aliases: list[tuple[str, str]] = []

    for doc in docs:
        category_id = str(doc.get("category_id") or "").strip()
        if not category_id:
            continue

        by_id[category_id] = doc

        aliases = doc.get("search_aliases") or {}
        for lang in SUPPORTED_LANGUAGES:
            for raw_alias in aliases.get(lang, []) or []:
                alias = _normalize_text(raw_alias)
                if not alias:
                    continue
                alias_to_id[alias] = category_id
                all_aliases.append((alias, category_id))

        # Keep direct translation fields searchable even if search_aliases is missing.
        for lang in SUPPORTED_LANGUAGES:
            t = (doc.get("translations") or {}).get(lang) or {}
            for key in ("category", "subcategory"):
                alias = _normalize_text(t.get(key))
                if not alias:
                    continue
                alias_to_id[alias] = category_id
                all_aliases.append((alias, category_id))

    payload = {"docs": by_id, "alias_to_id": alias_to_id, "all_aliases": all_aliases}

    with _CACHE_LOCK:
        _CACHE["docs"] = by_id
        _CACHE["alias_to_id"] = alias_to_id
        _CACHE["all_aliases"] = all_aliases
        _CACHE["expires_at"] = now + _CACHE_TTL_SECONDS

    return payload


def invalidate_workflow_cache() -> None:
    with _CACHE_LOCK:
        _CACHE["docs"] = {}
        _CACHE["alias_to_id"] = {}
        _CACHE["all_aliases"] = []
        _CACHE["expires_at"] = 0.0


def _normalized_documents(node: dict[str, Any]) -> list[str]:
    docs = node.get("documents_required")
    if isinstance(docs, list):
        return docs
    docs = node.get("required_documents")
    if isinstance(docs, list):
        return docs
    return []


def get_workflow(category_id: str, language: str | None = None) -> dict[str, Any] | None:
    if not category_id:
        return None

    cache = _load_cache()
    doc = cache["docs"].get(str(category_id).strip())
    if not doc:
        return None

    lang = _normalize_language(language)
    translations = doc.get("translations") or {}
    selected = translations.get(lang) or {}

    fallback_language = None
    if not selected:
        lang = DEFAULT_LANGUAGE
        selected = translations.get(lang) or {}
        fallback_language = lang

    if not selected:
        return None

    documents_required = _normalized_documents(selected)

    return {
        "category_id": doc.get("category_id", ""),
        "language": _normalize_language(language) if not fallback_language else fallback_language,
        "fallback_language": fallback_language,
        "category": selected.get("category", ""),
        "subcategory": selected.get("subcategory", ""),
        "problem_description": selected.get("problem_description", ""),
        "descriptions": list(selected.get("descriptions") or []),
        "workflow_steps": list(selected.get("workflow_steps") or []),
        "documents_required": documents_required,
        "required_documents": documents_required,
        "authorities": list(selected.get("authorities") or []),
        "escalation_path": list(selected.get("escalation_path") or []),
        "complaint_template": selected.get("complaint_template", ""),
        "online_portals": list(selected.get("online_portals") or []),
        "helplines": list(selected.get("helplines") or []),
    }


def resolve_category_id(*candidates: str, min_score: int = 82) -> str:
    cache = _load_cache()
    alias_to_id: dict[str, str] = cache["alias_to_id"]
    all_aliases: list[tuple[str, str]] = cache["all_aliases"]

    normalized_candidates = [_normalize_text(value) for value in candidates if _normalize_text(value)]
    if not normalized_candidates:
        return ""

    # Fast exact lookup.
    for value in normalized_candidates:
        exact = alias_to_id.get(value)
        if exact:
            return exact

    # Fuzzy fallback for minor spelling/romanization noise.
    best_id = ""
    best_score = 0
    for candidate in normalized_candidates:
        for alias, category_id in all_aliases:
            score = fuzz.ratio(candidate, alias)
            if score > best_score:
                best_score = score
                best_id = category_id

    if best_score >= min_score:
        return best_id
    return ""


def get_category_id_options() -> list[str]:
    """Return sorted available category IDs for constrained AI classification."""
    cache = _load_cache()
    return sorted(str(key) for key in cache["docs"].keys() if str(key).strip())


def localize_case_payload(case_data: dict[str, Any], language: str | None) -> dict[str, Any]:
    """Attach localized workflow fields to a case payload when category_id is resolvable."""
    if not case_data:
        return {}

    category_id = resolve_category_id(
        case_data.get("subcategory", ""),
        case_data.get("category", ""),
    )

    if not category_id:
        # Fallback to existing payload without crashing.
        payload = dict(case_data)
        docs = payload.get("required_documents") or payload.get("documents_required") or []
        payload["documents_required"] = list(docs)
        payload["required_documents"] = list(docs)
        return payload

    localized = get_workflow(category_id, language)
    if not localized:
        payload = dict(case_data)
        docs = payload.get("required_documents") or payload.get("documents_required") or []
        payload["documents_required"] = list(docs)
        payload["required_documents"] = list(docs)
        payload["category_id"] = category_id
        return payload

    merged = dict(case_data)
    merged.update(
        {
            "category_id": category_id,
            "category": localized.get("category", case_data.get("category", "")),
            "subcategory": localized.get("subcategory", case_data.get("subcategory", "")),
            "problem_description": localized.get("problem_description", case_data.get("problem_description", "")),
            "descriptions": localized.get("descriptions", case_data.get("descriptions", [])),
            "workflow_steps": localized.get("workflow_steps", case_data.get("workflow_steps", [])),
            "documents_required": localized.get("documents_required", []),
            "required_documents": localized.get("required_documents", []),
            "authorities": localized.get("authorities", case_data.get("authorities", [])),
            "escalation_path": localized.get("escalation_path", case_data.get("escalation_path", [])),
            "complaint_template": localized.get("complaint_template", case_data.get("complaint_template", "")),
            "online_portals": localized.get("online_portals", case_data.get("online_portals", [])),
            "helplines": localized.get("helplines", case_data.get("helplines", [])),
        }
    )
    return merged
