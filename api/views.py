from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# 🔥 Import your pipeline (make sure this exists)
try:
    from backend.query_processor import process_query
except ImportError:
    process_query = None


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

        # 🚨 If pipeline not connected yet
        if process_query is None:
            return JsonResponse({
                "status": "success",
                "query": query,
                "response": "Pipeline not connected yet",
                "confidence": 0.0
            })

        # 🔥 Call your real system
        result = process_query(query)

        return JsonResponse({
            "status": "success",
            "query": query,
            "response": result.get("response", ""),
            "confidence": result.get("confidence", 0.0),
            "data": result
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