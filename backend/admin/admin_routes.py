"""Admin management routes protected by JWT role checks."""

from __future__ import annotations

from bson import ObjectId
from rest_framework.decorators import api_view

from auth.auth_middleware import require_admin
from legal.admin_analytics import get_admin_queries, get_category_stats
from legal_cases.db_connection import get_collection
from legal_cases.response_utils import error_response, success_response


@api_view(["GET"])
@require_admin
def users_list(request):
    try:
        limit = min(max(int(request.query_params.get("limit", "50")), 1), 500)
        offset = max(int(request.query_params.get("offset", "0")), 0)
        cursor = (
            get_collection("users")
            .find({}, {"password_hash": 0})
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        rows = []
        for row in cursor:
            row["id"] = str(row.pop("_id"))
            rows.append(row)
        return success_response(rows, limit=limit, offset=offset, total=len(rows))
    except Exception:
        return error_response("Could not fetch users", status_code=500)


@api_view(["GET"])
@require_admin
def queries_list(request):
    try:
        limit = min(max(int(request.query_params.get("limit", "100")), 1), 500)
        offset = max(int(request.query_params.get("offset", "0")), 0)
        rows = get_admin_queries(limit=limit, offset=offset)
        return success_response(rows, limit=limit, offset=offset, total=len(rows))
    except Exception:
        return error_response("Could not fetch admin queries", status_code=500)


@api_view(["GET"])
@require_admin
def category_stats(request):
    try:
        return success_response(get_category_stats())
    except Exception:
        return error_response("Could not fetch category stats", status_code=500)


@api_view(["DELETE"])
@require_admin
def delete_query(request, query_id: str):
    try:
        result = get_collection("user_queries").delete_one({"_id": ObjectId(query_id)})
        if result.deleted_count == 0:
            return error_response("Query not found", status_code=404)
        return success_response({"deleted": True, "query_id": query_id})
    except Exception:
        return error_response("Could not delete query", status_code=500)
