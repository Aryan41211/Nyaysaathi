from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import md5

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from admin.service import get_query_by_id, log_classification_query
from ai_engine.pipeline import NyaySaathiPipeline
from auth.service import ensure_user_indexes
from middleware.auth_middleware import get_optional_current_user
from models.db import get_cache_collection, get_feedback_collection
from routes.admin_routes import router as admin_router
from routes.auth_routes import router as auth_router

app = FastAPI(title="NyaySaathi Semantic API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = NyaySaathiPipeline()


class ClassifyRequest(BaseModel):
    user_input: str
    user_id: str | None = None


class FeedbackRequest(BaseModel):
    query_id: str
    was_helpful: bool
    correct_category: str | None = None
    notes: str | None = None


def _input_hash(user_input: str) -> str:
    normalized = (user_input or "").strip().lower()
    return md5(normalized.encode("utf-8")).hexdigest()


def _confidence_message(confidence: float) -> str:
    if confidence >= 0.85:
        return "I am highly confident in this legal classification."
    if confidence >= 0.65:
        return "This looks like a strong match, but sharing one more detail can improve precision."
    return "This is a preliminary match. Please share a little more detail for higher accuracy."


def _read_cached_response(user_input: str) -> dict | None:
    cache = get_cache_collection()
    now = datetime.now(UTC)
    item = cache.find_one({"input_hash": _input_hash(user_input), "expires_at": {"$gt": now}})
    if not item:
        return None
    response = item.get("response")
    return response if isinstance(response, dict) else None


def _write_cached_response(user_input: str, response: dict) -> None:
    cache = get_cache_collection()
    now = datetime.now(UTC)
    cache.update_one(
        {"input_hash": _input_hash(user_input)},
        {
            "$set": {
                "response": response,
                "updated_at": now,
                "expires_at": now + timedelta(hours=12),
            }
        },
        upsert=True,
    )


@app.on_event("startup")
def startup() -> None:
    ensure_user_indexes()


app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _run_classification(payload: ClassifyRequest, request: Request) -> dict:
    cached = _read_cached_response(payload.user_input)
    if cached:
        return cached

    result = pipeline.process(payload.user_input)
    user = get_optional_current_user(request)

    effective_user_id = payload.user_id or (str(user.get("_id")) if user else None)
    effective_user_email = user.get("email") if user else None
    query_id = log_classification_query(
        user_input=payload.user_input,
        category=result.classification.category,
        subcategory=result.classification.subcategory,
        confidence=result.final_confidence,
        user_id=effective_user_id,
        user_email=effective_user_email,
    )

    response = {
        "query_id": query_id,
        "category": result.classification.category,
        "subcategory": result.classification.subcategory,
        "confidence": result.final_confidence,
        "user_message": _confidence_message(result.final_confidence),
        "intent_summary": result.classification.intent_summary,
        "assistant_response": result.assistant_response,
        "needs_clarification": result.classification.needs_clarification,
        "clarification_question": result.classification.clarification_question,
        "workflow_steps": result.workflow_steps,
        "required_documents": result.required_documents,
        "authorities": result.authorities,
        "relevant_laws": result.relevant_laws,
        "complaint_template": result.complaint_template,
        "online_portals": result.online_portals,
        "helplines": result.helplines,
        "embedding_score": result.embedding_score,
        "final_confidence": result.final_confidence,
    }

    _write_cached_response(payload.user_input, response)
    return response


@app.post("/classify")
def classify(payload: ClassifyRequest, request: Request) -> dict:
    return _run_classification(payload, request)


@app.post("/api/classify")
def classify_api(payload: ClassifyRequest, request: Request) -> dict:
    return _run_classification(payload, request)


@app.post("/api/feedback")
def submit_feedback(payload: FeedbackRequest) -> dict:
    source_query = get_query_by_id(payload.query_id)
    feedback = get_feedback_collection()
    feedback.insert_one(
        {
            "query_id": payload.query_id,
            "query_text": (source_query or {}).get("query_text", ""),
            "predicted_category": (source_query or {}).get("category"),
            "predicted_subcategory": (source_query or {}).get("subcategory"),
            "was_helpful": bool(payload.was_helpful),
            "correct_category": payload.correct_category,
            "notes": payload.notes,
            "created_at": datetime.now(UTC),
        }
    )
    return {"status": "received"}
