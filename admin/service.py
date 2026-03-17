from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from models.db import get_queries_collection, get_users_collection, get_workflows_collection


def list_users() -> list[dict[str, Any]]:
    users = get_users_collection()
    rows: list[dict[str, Any]] = []
    for user in users.find({}, {"password_hash": 0}).sort("created_at", -1):
        rows.append(
            {
                "id": str(user["_id"]),
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "role": user.get("role", "user"),
                "created_at": user.get("created_at"),
            }
        )
    return rows


def list_queries() -> list[dict[str, Any]]:
    queries = get_queries_collection()
    rows: list[dict[str, Any]] = []
    for query in queries.find({}).sort("created_at", -1).limit(500):
        rows.append(
            {
                "id": str(query["_id"]),
                "user_id": query.get("user_id"),
                "user_email": query.get("user_email"),
                "query_text": query.get("query_text"),
                "category": query.get("category"),
                "subcategory": query.get("subcategory"),
                "created_at": query.get("created_at"),
            }
        )
    return rows


def create_workflow(payload: dict[str, Any]) -> dict[str, str]:
    workflows = get_workflows_collection()
    doc = dict(payload)
    doc["created_at"] = datetime.now(UTC)
    doc["updated_at"] = datetime.now(UTC)
    result = workflows.insert_one(doc)
    return {"workflow_id": str(result.inserted_id)}


def update_workflow(workflow_id: str, updates: dict[str, Any]) -> dict[str, str]:
    workflows = get_workflows_collection()
    try:
        object_id = ObjectId(workflow_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workflow id") from exc

    safe_updates = dict(updates)
    safe_updates.pop("_id", None)
    safe_updates["updated_at"] = datetime.now(UTC)
    result = workflows.update_one({"_id": object_id}, {"$set": safe_updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return {"status": "updated"}


def delete_workflow(workflow_id: str) -> dict[str, str]:
    workflows = get_workflows_collection()
    try:
        object_id = ObjectId(workflow_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workflow id") from exc

    result = workflows.delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return {"status": "deleted"}


def count_users() -> int:
    return get_users_collection().count_documents({})


def count_queries() -> int:
    return get_queries_collection().count_documents({})


def log_user_query(user: dict, query_text: str, category: str, subcategory: str) -> None:
    queries = get_queries_collection()
    queries.insert_one(
        {
            "user_id": str(user["_id"]),
            "user_email": user.get("email"),
            "query_text": query_text,
            "category": category,
            "subcategory": subcategory,
            "created_at": datetime.now(UTC),
        }
    )


def log_classification_query(
    user_input: str,
    category: str,
    subcategory: str,
    confidence: float,
    user_id: str | None = None,
    user_email: str | None = None,
) -> str:
    queries = get_queries_collection()
    result = queries.insert_one(
        {
            "user_id": user_id,
            "user_email": user_email,
            "query_text": user_input,
            "category": category,
            "subcategory": subcategory,
            "confidence": float(confidence),
            "created_at": datetime.now(UTC),
        }
    )
    return str(result.inserted_id)


def get_query_by_id(query_id: str) -> dict | None:
    queries = get_queries_collection()
    try:
        object_id = ObjectId(query_id)
    except Exception:
        return None
    return queries.find_one({"_id": object_id})
