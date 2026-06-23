from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path

urlpatterns = [
    path('', lambda request: HttpResponse("ROOT WORKING")),
    path('health/', lambda request: JsonResponse({"status": "ok"})),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]
