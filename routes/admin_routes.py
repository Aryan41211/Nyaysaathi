from __future__ import annotations

from fastapi import APIRouter, Depends

from admin.service import (
    count_queries,
    count_users,
    create_workflow,
    delete_workflow,
    list_queries,
    list_users,
    update_workflow,
)
from middleware.admin_required import admin_required
from models.auth_models import WorkflowCreateRequest, WorkflowDeleteRequest, WorkflowUpdateRequest

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def get_admin_users(_: dict = Depends(admin_required)) -> dict:
    users = list_users()
    return {"total_users": count_users(), "users": users}


@router.get("/queries")
def get_admin_queries(_: dict = Depends(admin_required)) -> dict:
    queries = list_queries()
    return {"total_queries": count_queries(), "queries": queries}


@router.post("/workflows")
def post_admin_workflows(payload: WorkflowCreateRequest, _: dict = Depends(admin_required)) -> dict:
    return create_workflow(payload.payload)


@router.put("/workflows")
def put_admin_workflows(payload: WorkflowUpdateRequest, _: dict = Depends(admin_required)) -> dict:
    return update_workflow(payload.workflow_id, payload.updates)


@router.delete("/workflows")
def delete_admin_workflows(payload: WorkflowDeleteRequest, _: dict = Depends(admin_required)) -> dict:
    return delete_workflow(payload.workflow_id)
