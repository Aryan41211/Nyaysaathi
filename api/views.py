from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import re
from urllib.parse import unquote

from api.data_loader import CASES
from api.nlp.semantic_engine import get_semantic_engine
from api.nlp.query_processor import process_query


def health_check(request):
    return JsonResponse({
        "status": "ok",
        "message": "NyayaSaathi backend is running"
    })


def _norm(value: str) -> str:
    return " ".join((value or "").strip().lower().replace("/", " ").split())


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower())
    return slug.strip("-")


def _case_id(case: dict, index: int = 0) -> str:
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


def _with_case_id(case: dict, index: int = 0) -> dict:
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


def _all_cases() -> list:
    records = []
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


def _find_case_by_key(case_key: str):
    decoded = unquote(case_key or "")
    target_norm = _norm(decoded)
    target_slug = _slugify(decoded)

    for candidate in _all_cases():
        if _norm(candidate["id"]) == target_norm or candidate["id"] == target_slug:
            return candidate

    # Backward compatibility: old links may still pass subcategory text.
    for candidate in _all_cases():
        sub = str(candidate.get("subcategory", ""))
        if _norm(sub) == target_norm:
            return candidate

    # Fallback: partial containment match for minor punctuation/spacing drift.
    for candidate in _all_cases():
        sub = _norm(str(candidate.get("subcategory", "")))
        if target_norm and (target_norm in sub or sub in target_norm):
            return candidate

    return None


def categories(request):
    category_map = {}
    for case in _all_cases():
        category = str(case.get("category", "")).strip()
        if not category:
            continue
        category_map.setdefault(category, 0)
        category_map[category] += 1

    data = [
        {"category": category, "subcategory_count": count}
        for category, count in sorted(category_map.items(), key=lambda x: x[0].lower())
    ]
    return JsonResponse({"status": "success", "data": data})


def cases(request):
    category_filter = str(request.GET.get("category", "")).strip().lower()

    with_ids = _all_cases()

    if category_filter:
        filtered = [
            case for case in with_ids
            if str(case.get("category", "")).strip().lower() == category_filter
        ]
    else:
        filtered = with_ids

    return JsonResponse({"status": "success", "data": filtered})


def case_detail(request, subcategory):
    case = _find_case_by_key(subcategory)
    if not case:
        return JsonResponse({"status": "fail", "error": "Case not found"}, status=404)

    return JsonResponse({"status": "success", "data": case})


@csrf_exempt
def search(request):

    if request.method == "OPTIONS":
        return JsonResponse({}, status=200)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            query = data.get("query", "").strip()

            if not query:
                return JsonResponse({
                    "status": "fail",
                    "message": "Empty query"
                }, status=400)

            response = process_query(query, top_k=5)
            if isinstance(response, dict) and isinstance(response.get("data"), list):
                response["data"] = [
                    _with_case_id(case, idx)
                    for idx, case in enumerate(response["data"])
                ]
            status_code = 200 if response.get("status") != "error" else 500
            return JsonResponse(response, status=status_code)

        except Exception as e:
            return JsonResponse({
                "status": "error",
                "error": str(e)
            }, status=500)

    return JsonResponse({
        "status": "fail",
        "message": "Use POST method"
    }, status=405)