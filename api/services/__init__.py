import json
from typing import Any, Dict, List

from api.domain.response import error_envelope, success_envelope
from api.repositories.case_repository import CaseRepository
from legal_cases.views import generate_legal_guidance


class SearchService:
    def __init__(self, *, case_repo: CaseRepository):
        self.case_repo = case_repo

    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "service": "nyaysaathi", "message": "NyayaSaathi backend is running"}

    def categories(self) -> Dict[str, Any]:
        category_map: Dict[str, int] = {}
        for case in self.case_repo.all_cases():
            category = str(case.get("category", "")).strip()
            if not category:
                continue
            category_map.setdefault(category, 0)
            category_map[category] += 1

        data = [
            {"category": category, "subcategory_count": count}
            for category, count in sorted(category_map.items(), key=lambda x: x[0].lower())
        ]
        return {"status": "success", "data": data}

    def cases(self, *, category_filter: str) -> Dict[str, Any]:
        category_filter = (category_filter or "").strip().lower()
        with_ids = self.case_repo.all_cases()

        if category_filter:
            filtered = [
                case for case in with_ids
                if str(case.get("category", "")).strip().lower() == category_filter
            ]
        else:
            filtered = with_ids

        return {"status": "success", "data": filtered}

    def case_detail(self, *, subcategory: str) -> Dict[str, Any]:
        case = self.case_repo.find_case_by_key(subcategory)
        if not case:
            return error_envelope("Case not found", code="fail")
        return {"status": "success", "data": case}

    def search(self, *, query: str, top_k: int = 5) -> Dict[str, Any]:
        if not query:
            return error_envelope("Empty query", code="fail")

        # Compatibility: tests patch `legal_cases.views.generate_legal_guidance`.
        response = generate_legal_guidance(query, top_k=top_k)

        # Normalize mocked contracts so `success` is always present.
        if isinstance(response, dict) and "success" not in response:
            response["success"] = True

        # Enrich cases if the mocked/real response returns `data` as case dicts.
        if isinstance(response, dict) and isinstance(response.get("data"), list):
            response["data"] = [
                # Re-using CaseRepository normalization by mapping fields into stable shape
                # (best-effort; in tests, mocked data may be empty)
                self._with_case_ids(case_item, idx)
                for idx, case_item in enumerate(response["data"])
            ]

        # Preserve existing behavior: status_code computed by controller.
        return response

    def _with_case_ids(self, case_item: Dict[str, Any], idx: int) -> Dict[str, Any]:
        # If case_item is already a normalized case, keep it.
        if isinstance(case_item, dict) and "id" in case_item and "documents" in case_item:
            return case_item

        # Best-effort: run through the repository's enrichment by selecting a canonical case.
        # Since repository enrichment requires the original dataset item, we cannot perfectly
        # rebuild here without the source record. For now, keep the item and add minimal keys.
        enriched = dict(case_item or {})
        if "title" not in enriched:
            enriched["title"] = str(enriched.get("title") or enriched.get("subcategory") or "Legal Guidance")
        if "steps" not in enriched:
            enriched["steps"] = enriched.get("workflow_steps", [])
        if "documents" not in enriched:
            enriched["documents"] = enriched.get("required_documents", [])
        if "id" not in enriched:
            enriched["id"] = f"case-{idx}"
            enriched["slug"] = enriched["id"]
        return enriched
