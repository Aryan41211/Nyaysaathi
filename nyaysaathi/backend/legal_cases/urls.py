from django.urls import path
from . import views

urlpatterns = [
    path("categories/",          views.categories_list, name="categories"),
    path("cases/",               views.cases_list,      name="cases"),
    path("search/",              views.search,          name="search"),
    path("health/ai/",           views.ai_health,       name="ai_health"),
    path("case/<str:subcategory>/", views.case_detail,  name="case_detail"),
]
