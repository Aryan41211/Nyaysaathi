from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    category: str = "unknown"
    subcategory: str = "unknown"
    intent_summary: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    needs_clarification: bool = True
    clarification_question: str = "Please share more details so I can classify your issue accurately."
    secondary_category: str | None = None
    extracted_facts: dict[str, Any] = Field(default_factory=dict)


class PipelineResponse(BaseModel):
    classification: ClassificationResult
    guidance: str
    assistant_response: str = ""
    relevant_laws: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    authorities: list[Any] = Field(default_factory=list)
    complaint_template: str | None = None
    online_portals: list[str] = Field(default_factory=list)
    helplines: list[str] = Field(default_factory=list)
    embedding_score: float = Field(default=0.0, ge=0.0, le=1.0)
    llm_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    final_confidence: float = Field(default=0.0, ge=0.0, le=1.0)