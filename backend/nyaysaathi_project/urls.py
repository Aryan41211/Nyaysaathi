from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def api_health(request):
    return JsonResponse({"status": "ok"})


def health(request):
    return JsonResponse({"status": "ok", "service": "NyaySaathi API", "version": "1.0.0"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health", api_health),
    path("api/", include("legal_cases.urls")),
    path("api/auth/", include("auth.urls")),
    path("api/admin/", include("admin.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("health/", health),
]
