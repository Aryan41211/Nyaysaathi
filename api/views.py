from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from importlib import import_module


def _get_process_query():
    """Dynamically resolve the optional pipeline function if present."""
    try:
        module = import_module("backend.query_processor")
        return getattr(module, "process_query", None)
    except Exception:
        return None


def health_check(request):
    return JsonResponse({
        "status": "ok",
        "message": "DEPLOY TEST SUCCESS"
    })

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def search(request):

    # ✅ Allow preflight request
    if request.method == "OPTIONS":
        return JsonResponse({}, status=200)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            query = data.get("query", "")

            return JsonResponse({
                "query": query,
                "response": "Processing will be added soon",
                "confidence": 0.0,
                "status": "success"
            })

        except Exception as e:
            return JsonResponse({
                "error": str(e),
                "status": "error"
            })

    return JsonResponse({
        "message": "Use POST method",
        "status": "fail"
    }, status=405)