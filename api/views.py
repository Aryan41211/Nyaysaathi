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
        "message": "NyayaSaathi backend is running"
    })


@csrf_exempt
def search(request):
    if request.method != "POST":
        return JsonResponse({
            "status": "fail",
            "message": "Use POST method"
        }, status=405)

    try:
        data = json.loads(request.body)
        query = data.get("query", "").strip()

        # 🔍 Validate input
        if not query:
            return JsonResponse({
                "status": "fail",
                "message": "Query cannot be empty"
            }, status=400)

        process_query = _get_process_query()

        if process_query is None:
            return JsonResponse({
                "status": "success",
                "query": query,
                "response": "Pipeline not connected yet",
                "confidence": 0.0
            })

        result = process_query(query)

        if isinstance(result, dict):
            response_text = result.get("response", "")
            confidence = result.get("confidence", 0.0)
            data = result
        else:
            response_text = str(result)
            confidence = 0.0
            data = {"raw": result}

        return JsonResponse({
            "status": "success",
            "query": query,
            "response": response_text,
            "confidence": confidence,
            "data": data
        })

    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid JSON format"
        }, status=400)

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)