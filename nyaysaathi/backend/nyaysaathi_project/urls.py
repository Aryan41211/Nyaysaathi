from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok", "service": "NyaySaathi API", "version": "1.0.0"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("legal_cases.urls")),
    path("health/", health),
]
