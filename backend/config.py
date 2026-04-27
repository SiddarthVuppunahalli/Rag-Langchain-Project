from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(BASE_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env", override=False)


@dataclass(frozen=True)
class CompanyConfig:
    ticker: str
    company: str
    cik: str


TRACKED_COMPANIES = [
    CompanyConfig(ticker="AAPL", company="Apple Inc.", cik="0000320193"),
    CompanyConfig(ticker="MSFT", company="Microsoft Corporation", cik="0000789019"),
    CompanyConfig(ticker="NVDA", company="NVIDIA Corporation", cik="0001045810"),
]

TRACKED_FILING_TYPES = ["10-K", "10-Q"]

RAW_FILINGS_DIR = BASE_DIR / "data" / "raw_filings"
PARSED_FILINGS_DIR = BASE_DIR / "data" / "parsed_filings"
CHROMA_PATH = BASE_DIR / "chroma_db"
EVAL_RESULTS_DIR = BASE_DIR / "eval_results"

DEFAULT_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "900"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
DEFAULT_CHAT_MODEL = os.getenv("RAG_CHAT_MODEL", "gemini-2.5-flash")
DEFAULT_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "SEC Filing RAG Analyst contact@example.com",
)
