from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import PARSED_FILINGS_DIR, TRACKED_COMPANIES, TRACKED_FILING_TYPES
from rag_pipeline import get_rag_pipeline


app = FastAPI(title="SEC Filing RAG Analyst API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    company: str | None = None
    filing_type: str | None = None


class SourceItem(BaseModel):
    company: str
    ticker: str
    filing_type: str
    filing_date: str
    section: str
    section_heading: str
    excerpt: str
    source_file: str
    source_url: str


class ChatResponse(BaseModel):
    answer: str
    retrieval_count: int
    sources: list[SourceItem]
    metrics: dict[str, float | int]


def read_available_filings() -> list[dict]:
    filings: list[dict] = []
    for json_file in sorted(PARSED_FILINGS_DIR.glob("*/*/*.json")):
        payload = json.loads(json_file.read_text(encoding="utf-8"))
        filings.append(
            {
                "ticker": payload["ticker"],
                "filing_type": payload["filing_type"],
                "filing_date": payload["filing_date"],
                "accession_number": payload["accession_number"],
                "section_count": payload["section_count"],
            }
        )
    return filings


try:
    rag_pipeline = get_rag_pipeline()
except Exception as exc:
    rag_pipeline = None
    print(f"Warning: SEC RAG pipeline failed to initialize: {exc}")


@app.get("/api/companies")
async def companies_endpoint():
    return [{"ticker": item.ticker, "company": item.company} for item in TRACKED_COMPANIES]


@app.get("/api/filings")
async def filings_endpoint():
    return read_available_filings()


@app.get("/api/filters")
async def filters_endpoint():
    return {
        "filing_types": TRACKED_FILING_TYPES,
        "companies": [{"ticker": item.ticker, "company": item.company} for item in TRACKED_COMPANIES],
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not rag_pipeline:
        raise HTTPException(
            status_code=500,
            detail="RAG pipeline not initialized. Ensure embeddings are ingested and GOOGLE_API_KEY is set.",
        )

    try:
        response = rag_pipeline.answer(
            question=request.message,
            company=request.company,
            filing_type=request.filing_type,
        )

        sources = [
            SourceItem(
                company=document.metadata.get("company", document.metadata.get("ticker", "Unknown")),
                ticker=document.metadata.get("ticker", "Unknown"),
                filing_type=document.metadata.get("filing_type", "Unknown"),
                filing_date=document.metadata.get("filing_date", "Unknown"),
                section=document.metadata.get("section", "unknown"),
                section_heading=document.metadata.get("section_heading", "Unknown"),
                excerpt=" ".join(document.page_content.split())[:320],
                source_file=document.metadata.get("source_file", ""),
                source_url=document.metadata.get("source_url", ""),
            )
            for document in response["context"]
        ]
        return ChatResponse(
            answer=response["answer"],
            retrieval_count=response["retrieval_count"],
            sources=sources,
            metrics=response["metrics"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
