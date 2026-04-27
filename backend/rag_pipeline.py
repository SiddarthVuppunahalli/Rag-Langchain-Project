from __future__ import annotations

from time import perf_counter
from typing import Any

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings

from config import (
    CHROMA_PATH,
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_TOP_K,
    GOOGLE_API_KEY,
)


SYSTEM_PROMPT = """You are an SEC filings research assistant.

Answer the user's question using only the retrieved filing excerpts. If the context does not
support the answer, say that you do not have enough evidence from the available filings.

When you answer:
- Prioritize precise, evidence-backed language.
- Mention the company and filing type when relevant.
- Keep the answer concise but substantive.
- Do not invent financial facts that are not in the retrieved excerpts.
"""

SECTION_INTENT_RULES = {
    "risk_factors": [
        "risk",
        "risks",
        "competition",
        "competitive",
        "concentration",
        "supplier",
        "supply",
        "manufacturing",
        "dependence",
        "inventory",
        "customer concentration",
    ],
    "mda": [
        "revenue",
        "operating",
        "performance",
        "results",
        "quarter",
        "demand",
        "momentum",
        "growth",
        "margin",
        "profitability",
        "commentary",
    ],
    "business": [
        "business",
        "segment",
        "segments",
        "offerings",
        "products",
        "services",
        "platforms",
        "markets",
        "describe",
    ],
}


def format_context(documents: list[Document]) -> str:
    sections: list[str] = []
    for index, document in enumerate(documents, start=1):
        metadata = document.metadata
        sections.append(
            "\n".join(
                [
                    f"[Source {index}]",
                    f"Ticker: {metadata.get('ticker', 'Unknown')}",
                    f"Filing Type: {metadata.get('filing_type', 'Unknown')}",
                    f"Filing Date: {metadata.get('filing_date', 'Unknown')}",
                    f"Section: {metadata.get('section_heading', metadata.get('section', 'Unknown'))}",
                    document.page_content,
                ]
            )
        )
    return "\n\n".join(sections)


def build_filter(company: str | None = None, filing_type: str | None = None) -> dict[str, Any] | None:
    clauses: list[dict[str, Any]] = []
    if company:
        clauses.append({"ticker": company.upper()})
    if filing_type:
        clauses.append({"filing_type": filing_type.upper()})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def combine_filters(
    base_filter: dict[str, Any] | None,
    extra_filter: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not base_filter:
        return extra_filter
    if not extra_filter:
        return base_filter
    return {"$and": [base_filter, extra_filter]}


def infer_section_priority(question: str) -> list[str]:
    normalized_question = question.lower()
    scores: list[tuple[str, int]] = []

    for section, keywords in SECTION_INTENT_RULES.items():
        score = sum(1 for keyword in keywords if keyword in normalized_question)
        scores.append((section, score))

    ranked_sections = [section for section, score in sorted(scores, key=lambda item: item[1], reverse=True) if score > 0]
    fallback_order = ["mda", "business", "risk_factors"]
    for section in fallback_order:
        if section not in ranked_sections:
            ranked_sections.append(section)
    return ranked_sections


class SecRagPipeline:
    def __init__(self) -> None:
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set. Add it to backend/.env or the project .env.")

        embeddings = HuggingFaceEmbeddings(model_name=DEFAULT_EMBEDDING_MODEL)
        self.vectorstore = Chroma(
            persist_directory=str(CHROMA_PATH),
            embedding_function=embeddings,
        )
        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_CHAT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0,
        )

    def retrieve(
        self,
        question: str,
        company: str | None = None,
        filing_type: str | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> list[Document]:
        base_filter = build_filter(company=company, filing_type=filing_type)
        section_priority = infer_section_priority(question)

        gathered_documents: list[Document] = []
        seen_chunk_ids: set[str] = set()

        for section in section_priority:
            if len(gathered_documents) >= top_k:
                break

            section_filter = combine_filters(base_filter, {"section": section})
            section_retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": top_k, "filter": section_filter} if section_filter else {"k": top_k}
            )
            for document in section_retriever.invoke(question):
                chunk_id = document.metadata.get("chunk_id")
                if chunk_id in seen_chunk_ids:
                    continue
                gathered_documents.append(document)
                if chunk_id:
                    seen_chunk_ids.add(chunk_id)
                if len(gathered_documents) >= top_k:
                    break

        if len(gathered_documents) < top_k:
            fallback_kwargs: dict[str, Any] = {"k": top_k}
            if base_filter:
                fallback_kwargs["filter"] = base_filter
            fallback_retriever = self.vectorstore.as_retriever(search_kwargs=fallback_kwargs)
            for document in fallback_retriever.invoke(question):
                chunk_id = document.metadata.get("chunk_id")
                if chunk_id in seen_chunk_ids:
                    continue
                gathered_documents.append(document)
                if chunk_id:
                    seen_chunk_ids.add(chunk_id)
                if len(gathered_documents) >= top_k:
                    break

        return gathered_documents[:top_k]

    def answer(
        self,
        question: str,
        company: str | None = None,
        filing_type: str | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> dict[str, Any]:
        started_at = perf_counter()
        retrieval_started_at = perf_counter()
        documents = self.retrieve(
            question=question,
            company=company,
            filing_type=filing_type,
            top_k=top_k,
        )
        retrieval_ms = (perf_counter() - retrieval_started_at) * 1000

        context = format_context(documents)
        prompt = f"{SYSTEM_PROMPT}\n\nQuestion:\n{question}\n\nContext:\n{context}"
        generation_started_at = perf_counter()
        answer = self.llm.invoke(prompt).content
        generation_ms = (perf_counter() - generation_started_at) * 1000
        total_ms = (perf_counter() - started_at) * 1000

        return {
            "answer": answer,
            "context": documents,
            "retrieval_count": len(documents),
            "metrics": {
                "retrieval_ms": round(retrieval_ms, 2),
                "generation_ms": round(generation_ms, 2),
                "total_ms": round(total_ms, 2),
                "context_characters": len(context),
            },
        }


def get_rag_pipeline() -> SecRagPipeline:
    return SecRagPipeline()
