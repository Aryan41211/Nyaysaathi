from django.urls import path
from .views import health_check, search

urlpatterns = [
path('health/', health_check),
path('search/', search),
]
