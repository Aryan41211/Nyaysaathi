from django.urls import path
from .views import case_detail, cases, categories, health_check, search

urlpatterns = [
    path('health/', health_check),
    path('search/', search),
    path('categories/', categories),
    path('cases/', cases),
    path('case/<path:subcategory>/', case_detail),
    path('case/<path:subcategory>', case_detail),
]