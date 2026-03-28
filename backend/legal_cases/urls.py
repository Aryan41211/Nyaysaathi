from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("observability/", views.observability_snapshot, name="observability_snapshot"),
    path("feedback/", views.feedback, name="feedback"),
    path("search/async", views.search_async_submit, name="search_async_submit"),
    path("search/async/", views.search_async_submit, name="search_async_submit_slash"),
    path("search/async/<str:task_id>/", views.search_async_status, name="search_async_status"),
    path("categories/", views.categories_list, name="categories"),
    path("cases/", views.cases_list, name="cases"),
    path("classify", views.classify),
    path("classify/", views.classify, name="classify"),
    path("search", views.search),
    path("search/", views.search, name="search"),
    path("user/history/", views.user_history, name="user_history"),
    path("health/ai/", views.ai_health, name="ai_health"),
    path("case/<path:subcategory>/", views.case_detail, name="case_detail"),
]
