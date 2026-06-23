import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from api.repositories.case_repository import CaseRepository
from api.services.search_service import SearchService


def _service() -> SearchService:
    return SearchService(case_repo=CaseRepository())


def health_check(request):
    return JsonResponse(_service().health())


def categories(request):
    return JsonResponse(_service().categories())


def cases(request):
    return JsonResponse(_service().cases(category_filter=request.GET.get("category", "")))


def case_detail(request, subcategory):
    payload = _service().case_detail(subcategory=subcategory)
    # Match legacy api/views.py behavior: 404 only when status is fail (case not found).
    status = 404 if isinstance(payload, dict) and payload.get("status") == "fail" else 200
    return JsonResponse(payload, status=status)


@csrf_exempt
def search(request):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=200)

    if request.method in ("GET", "POST"):
        if request.method == "GET":
            query = str(request.GET.get("query", "")).strip()
        else:
            data = json.loads(request.body or "{}")
            query = str(data.get("query", "")).strip()

        response = _service().search(query=query, top_k=5)

        # Preserve previous controller status-code behavior where possible.
        status = 200
        if isinstance(response, dict) and response.get("status") == "error":
            status = 500
        if isinstance(response, dict) and response.get("error"):
            status = 400 if str(response.get("status")) == "fail" else 500

        return JsonResponse(response, status=status)

    return JsonResponse({"status": "fail", "message": "Use GET or POST method"}, status=405)
