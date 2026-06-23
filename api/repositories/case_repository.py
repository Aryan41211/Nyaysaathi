import re
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from api.data_loader import CASES
from api.nlp.semantic_engine import get_semantic_engine


def _norm(value: str) -> str:
    return " ".join((value or "").strip().lower().replace("/", " ").split())


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower())
    return slug.strip("-")


def _case_id(case: Dict[str, Any], index: int = 0) -> str:
    explicit = str(case.get("id", "")).strip()
    # Ignore ephemeral semantic-engine IDs like source:idx.
    if explicit and not re.match(r"^.+:\d+$", explicit):
        normalized = _slugify(explicit)
        if normalized:
            return normalized

    explicit_slug = str(case.get("slug", "")).strip()
    if explicit_slug:
        normalized_slug = _slugify(explicit_slug)
        if normalized_slug:
            return normalized_slug

    category = str(case.get("category", "")).strip()
    subcategory = str(case.get("subcategory", "")).strip()
    from_sub = _slugify(subcategory)
    from_category = _slugify(category)
    if from_sub:
        return from_sub
    if from_category:
        return f"{from_category}-case-{index}"

    return f"case-{index}"


def _with_case_id(case: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    enriched = dict(case)
    case_id = _case_id(enriched, index)
    enriched["id"] = case_id
    enriched["slug"] = case_id
    enriched["title"] = str(enriched.get("title") or enriched.get("subcategory") or "Legal Guidance")
    if "steps" not in enriched:
        enriched["steps"] = enriched.get("workflow_steps", [])
    if "documents" not in enriched:
        enriched["documents"] = enriched.get("required_documents", [])
    return enriched


class CaseRepository:
    def all_cases(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        seen = set()

        for idx, case in enumerate(CASES):
            enriched = _with_case_id(case, idx)
            key = (
                _norm(str(enriched.get("category", ""))),
                _norm(str(enriched.get("subcategory", ""))),
                _norm(str(enriched.get("problem_description", ""))),
            )
            if key in seen:
                continue
            seen.add(key)
            records.append(enriched)

        try:
            semantic_cases = get_semantic_engine().get_cases()
        except Exception:
            semantic_cases = []

        offset = len(records)
        for idx, case in enumerate(semantic_cases):
            enriched = _with_case_id(case, offset + idx)
            key = (
                _norm(str(enriched.get("category", ""))),
                _norm(str(enriched.get("subcategory", ""))),
                _norm(str(enriched.get("problem_description", ""))),
            )
            if key in seen:
                continue
            seen.add(key)
            records.append(enriched)

        return records

    def find_case_by_key(self, case_key: str) -> Optional[Dict[str, Any]]:
        decoded = unquote(case_key or "")
        target_norm = _norm(decoded)
        target_slug = _slugify(decoded)

        for candidate in self.all_cases():
            if _norm(candidate["id"]) == target_norm or candidate["id"] == target_slug:
                return candidate

        # Backward compatibility: old links may still pass subcategory text.
        for candidate in self.all_cases():
            sub = str(candidate.get("subcategory", ""))
            if _norm(sub) == target_norm:
                return candidate

        # Fallback: partial containment match for minor punctuation/spacing drift.
        for candidate in self.all_cases():
            sub = _norm(str(candidate.get("subcategory", "")))
            if target_norm and (target_norm in sub or sub in target_norm):
                return candidate

        return None
