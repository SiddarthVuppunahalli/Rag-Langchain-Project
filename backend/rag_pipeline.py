from __future__ import annotations

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
    filters: dict[str, Any] = {}
    if company:
        filters["ticker"] = company.upper()
    if filing_type:
        filters["filing_type"] = filing_type.upper()
    return filters or None


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
        search_kwargs: dict[str, Any] = {"k": top_k}
        metadata_filter = build_filter(company=company, filing_type=filing_type)
        if metadata_filter:
            search_kwargs["filter"] = metadata_filter

        retriever = self.vectorstore.as_retriever(search_kwargs=search_kwargs)
        return retriever.invoke(question)

    def answer(
        self,
        question: str,
        company: str | None = None,
        filing_type: str | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> dict[str, Any]:
        documents = self.retrieve(
            question=question,
            company=company,
            filing_type=filing_type,
            top_k=top_k,
        )

        context = format_context(documents)
        prompt = f"{SYSTEM_PROMPT}\n\nQuestion:\n{question}\n\nContext:\n{context}"
        answer = self.llm.invoke(prompt).content

        return {
            "answer": answer,
            "context": documents,
            "retrieval_count": len(documents),
        }


def get_rag_pipeline() -> SecRagPipeline:
    return SecRagPipeline()
