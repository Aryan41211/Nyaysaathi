from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from api.nlp.query_processor import process_query


def health_check(request):
    return JsonResponse({
        "status": "ok",
        "message": "NyayaSaathi backend is running"
    })


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