from django.urls import path

from . import admin_routes

urlpatterns = [
    path("users", admin_routes.users_list, name="admin-users"),
    path("queries", admin_routes.queries_list, name="admin-queries"),
    path("query-stats", admin_routes.category_stats, name="admin-query-stats"),
    path("queries/<str:query_id>", admin_routes.delete_query, name="admin-query-delete"),
]
