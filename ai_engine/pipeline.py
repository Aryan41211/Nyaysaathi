from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from ai_engine.classifier import LLMClassifier
from ai_engine.embedder import CANONICAL_CATEGORY_MAP, SemanticEmbedder
from ai_engine.fusion import FusionScorer
from ai_engine.intent_router import IntentRouter
from ai_engine.preprocessor import Preprocessor
from ai_engine.reranker import ContextReranker
from ai_engine.responder import FriendlyResponder
from models.schemas import ClassificationResult, PipelineResponse


class NyaySaathiPipeline:
    def __init__(self) -> None:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        self.preprocessor = Preprocessor()
        self.classifier = LLMClassifier()
        self.embedder = SemanticEmbedder()
        self.fusion = FusionScorer()
        self.dataset = self._load_dataset()
        self.router = IntentRouter(self.dataset)
        self.context_reranker = ContextReranker()
        self.responder = FriendlyResponder()
        self.model_mode = (os.getenv("MODEL_MODE", "hybrid") or "hybrid").strip().lower()
        key = (os.getenv("OPENAI_API_KEY") or "").strip().lower()
        self.openai_available = bool(key and key not in {"your_key_here", "changeme", "none", "null"})

    def _load_dataset(self) -> list[dict]:
        path = Path(__file__).resolve().parents[1] / "data" / "legal_categories.json"
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _canonical_category(self, category_text: str) -> str:
        return CANONICAL_CATEGORY_MAP.get(str(category_text).strip().lower(), "unknown")

    def _lookup_entry(self, llm_category: str, llm_subcategory: str, top_embed: dict | None) -> dict | None:
        llm_sub = str(llm_subcategory or "").strip().lower()
        for entry in self.dataset:
            if str(entry.get("subcategory", "")).strip().lower() == llm_sub:
                return entry

        if top_embed:
            embed_sub = str(top_embed.get("subcategory", "")).strip().lower()
            for entry in self.dataset:
                if str(entry.get("subcategory", "")).strip().lower() == embed_sub:
                    return entry

        for entry in self.dataset:
            if self._canonical_category(entry.get("category", "")) == llm_category:
                return entry

        return None

    @staticmethod
    def _extract_relevant_laws(entry: dict) -> list[str]:
        for key in ("relevant_laws", "applicable_laws", "laws"):
            value = entry.get(key)
            if isinstance(value, list):
                return [str(x) for x in value if str(x).strip()]
            if isinstance(value, str) and value.strip():
                return [value.strip()]
        return []

    async def _process_async(self, user_input: str) -> PipelineResponse:
        clean_text = self.preprocessor.process(user_input)
        embed_matches = await asyncio.to_thread(self.embedder.top_k_matches, clean_text, 8)
        embed_matches = self.context_reranker.rerank(clean_text, embed_matches)
        top_embed = embed_matches[0] if embed_matches else None
        reranked_entry, reranked_score, secondary_entry = self.router.rerank(clean_text, embed_matches)
        if reranked_entry is not None:
            top_embed = {
                "category_id": self.router.category_id(str(reranked_entry.get("category", ""))),
                "subcategory": str(reranked_entry.get("subcategory", "")),
                "score": reranked_score,
            }
            embed_matches = [top_embed, *[m for m in embed_matches if m.get("subcategory") != top_embed["subcategory"]]]

        use_embedding_only = self.model_mode == "embedding" or not self.openai_available

        if use_embedding_only:
            llm_result = ClassificationResult(
                category=str((top_embed or {}).get("category_id") or "consumer_complaints"),
                subcategory=str((top_embed or {}).get("subcategory") or "General Grievance"),
                intent_summary=f"Classified via embedding-only mode for: {clean_text[:120]}",
                confidence=float((top_embed or {}).get("score", 0.55)),
                needs_clarification=False,
                clarification_question="",
                extracted_facts={"mode": "embedding_only"},
            )
            llm_available = False
        else:
            llm_result = await asyncio.to_thread(self.classifier.classify, clean_text, top_embed)
            llm_available = self.classifier.last_llm_available

        fused = self.fusion.fuse(llm_result, embed_matches, llm_available=llm_available)
        top_embed = fused["top_embed"]
        entry = self._lookup_entry(llm_result.category, llm_result.subcategory, top_embed)
        if entry is None and reranked_entry is not None:
            entry = reranked_entry

        if fused["needs_clarification"]:
            clarification_result = llm_result.model_copy(
                update={
                    "needs_clarification": True,
                    "clarification_question": fused["clarification_question"],
                    "confidence": fused["final_confidence"],
                }
            )
            assistant_response = self.responder.generate(
                query=user_input,
                category=clarification_result.category,
                subcategory=clarification_result.subcategory,
                confidence=fused["final_confidence"],
                workflow_steps=list((entry or {}).get("workflow_steps") or []),
                needs_clarification=True,
                clarification_question=fused["clarification_question"],
            )
            return PipelineResponse(
                classification=clarification_result,
                guidance=fused["clarification_question"] or "Please share one-line details about what happened, when, and who is involved.",
                assistant_response=assistant_response,
                relevant_laws=[],
                next_steps=list((entry or {}).get("workflow_steps") or []),
                workflow_steps=list((entry or {}).get("workflow_steps") or []),
                required_documents=list((entry or {}).get("required_documents") or []),
                authorities=list((entry or {}).get("authorities") or []),
                complaint_template=(entry or {}).get("complaint_template"),
                online_portals=list((entry or {}).get("online_portals") or []),
                helplines=list((entry or {}).get("helplines") or []),
                embedding_score=fused["embed_score"],
                llm_confidence=fused["llm_score"],
                final_confidence=fused["final_confidence"],
            )

        if not entry:
            no_map_result = llm_result.model_copy(
                update={
                    "confidence": fused["final_confidence"],
                    "needs_clarification": True,
                    "clarification_question": "Please provide more details so the issue can be mapped to a legal workflow.",
                }
            )
            assistant_response = self.responder.generate(
                query=user_input,
                category=no_map_result.category,
                subcategory=no_map_result.subcategory,
                confidence=fused["final_confidence"],
                workflow_steps=[],
                needs_clarification=True,
                clarification_question=no_map_result.clarification_question,
            )
            return PipelineResponse(
                classification=no_map_result,
                guidance="Could not map to a legal workflow confidently.",
                assistant_response=assistant_response,
                relevant_laws=[],
                next_steps=[],
                workflow_steps=[],
                required_documents=[],
                authorities=[],
                complaint_template=None,
                online_portals=[],
                helplines=[],
                embedding_score=fused["embed_score"],
                llm_confidence=fused["llm_score"],
                final_confidence=fused["final_confidence"],
            )

        guidance = (
            f"Matched workflow: {entry.get('subcategory', 'Unknown')} under "
            f"{entry.get('category', 'Unknown')}. Follow the recommended next steps and authorities."
        )

        final_classification = llm_result.model_copy(
            update={
                "subcategory": str(entry.get("subcategory", llm_result.subcategory)),
                "category": str(top_embed.get("category_id", llm_result.category)) if top_embed else llm_result.category,
                "secondary_category": self.router.category_id(str((secondary_entry or {}).get("category", ""))) if secondary_entry else None,
                "confidence": fused["final_confidence"],
                "needs_clarification": False,
            }
        )
        assistant_response = self.responder.generate(
            query=user_input,
            category=final_classification.category,
            subcategory=final_classification.subcategory,
            confidence=fused["final_confidence"],
            workflow_steps=list(entry.get("workflow_steps") or []),
            needs_clarification=False,
            clarification_question="",
        )

        return PipelineResponse(
            classification=final_classification,
            guidance=guidance,
            assistant_response=assistant_response,
            relevant_laws=self._extract_relevant_laws(entry),
            next_steps=list(entry.get("workflow_steps") or []),
            workflow_steps=list(entry.get("workflow_steps") or []),
            required_documents=list(entry.get("required_documents") or []),
            authorities=list(entry.get("authorities") or []),
            complaint_template=entry.get("complaint_template"),
            online_portals=list(entry.get("online_portals") or []),
            helplines=list(entry.get("helplines") or []),
            embedding_score=fused["embed_score"],
            llm_confidence=fused["llm_score"],
            final_confidence=fused["final_confidence"],
        )

    def process(self, user_input: str) -> PipelineResponse:
        return asyncio.run(self._process_async(user_input))