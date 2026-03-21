from django.urls import path
from . import views

urlpatterns = [
    path("categories/",          views.categories_list, name="categories"),
    path("cases/",               views.cases_list,      name="cases"),
    path("classify",             views.classify,        name="classify"),
    path("search/",              views.search,          name="search"),
    path("user/history",         views.user_history,    name="user_history"),
    path("admin/query-stats",    views.admin_query_stats, name="admin_query_stats"),
    path("admin/queries",        views.admin_queries,   name="admin_queries"),
    path("health/ai/",           views.ai_health,       name="ai_health"),
    path("case/<path:subcategory>/", views.case_detail,  name="case_detail"),
]
