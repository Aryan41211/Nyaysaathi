from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

urlpatterns = [
    path('', lambda request: HttpResponse("ROOT WORKING")),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]