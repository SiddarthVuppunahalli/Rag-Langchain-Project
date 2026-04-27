# SEC Filing RAG Analyst

A retrieval-augmented analysis system for SEC `10-K` and `10-Q` filings. The project is designed to show practical RAG engineering decisions rather than just a chat UI: section-aware ingestion, metadata-rich retrieval, source-grounded answers, and measurable evaluation outputs.

## Why This Project

SEC filings are a strong RAG domain because they are:

- long, messy, real-world documents
- rich in structure (`Business`, `Risk Factors`, `Management's Discussion and Analysis`)
- good for metadata filtering by company, filing type, and filing date
- realistic for evaluation because the questions can target specific sections and recent disclosures

## Current Architecture

```text
frontend/
  src/app/
    layout.tsx
    page.tsx
backend/
  config.py
  fetch_filings.py
  parse_filings.py
  ingest.py
  rag_pipeline.py
  main.py
  eval.py
  data/
    raw_filings/
    parsed_filings/
```

## Backend Flow

1. `fetch_filings.py`
- Downloads recent `10-K` and `10-Q` filings for a small tracked company list from SEC EDGAR.
- Saves a manifest with source metadata for later parsing and measurement.

2. `parse_filings.py`
- Cleans raw filing HTML.
- Extracts high-value sections for the MVP:
  - `business`
  - `risk_factors`
  - `mda`
- Writes parsed JSON files with section counts and text sizes.

3. `ingest.py`
- Converts parsed sections into chunked LangChain `Document` objects.
- Preserves chunk metadata including:
  - ticker
  - company
  - filing type
  - filing date
  - accession number
  - section
  - source URL
- Persists embeddings to Chroma.

4. `rag_pipeline.py`
- Uses LangChain for retrieval orchestration.
- Supports metadata-filtered retrieval by company and filing type.
- Returns both the answer and the retrieved source chunks.

5. `eval.py`
- Runs a small benchmark and saves measurable outputs such as:
  - average query latency
  - average retrieval count
  - section hit rate

## Measurement-First Design

The project is being built to support strong resume bullets later. That means we intentionally preserve numbers that can be reported, including:

- companies ingested
- filings downloaded
- sections extracted
- chunks embedded
- average retrieval count
- benchmark question count
- section hit rate
- average query latency

Later evaluation work can add:

- faithfulness
- answer relevancy
- context precision
- context recall
- improvement percentages across retrieval configurations

## Local Setup

### Backend

1. Create and activate a Python environment.
2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Create `backend/.env` or project-root `.env` with:

```bash
GOOGLE_API_KEY=your_gemini_api_key
SEC_USER_AGENT=Your Name your-email@example.com
```

The SEC asks automated clients to provide a descriptive `User-Agent`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

If needed, set:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Running The Pipeline

From `backend/`:

```bash
python fetch_filings.py
python parse_filings.py
python ingest.py
python main.py
```

Then start the frontend and open `http://localhost:3000`.
