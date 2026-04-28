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
- Runs a benchmark and saves measurable outputs such as:
  - average query latency
  - average retrieval count
  - section hit rate
  - split-level results across tuned and blind prompts

## Evaluation Approach

The retrieval benchmark is designed to measure whether the system lands in the right filing section before worrying about answer style.

- `backend/benchmarks/sec_benchmark.json` currently includes:
  - a `tuned` split with standard and harder indirect questions
  - a `blind` split with alternate phrasing intended to be less coupled to the retrieval heuristic
- each benchmark case records:
  - company
  - expected filing type
  - expected section
  - expected answer keywords
- `backend/eval.py` compares retrieval configurations and writes:
  - row-level CSV output
  - JSON summaries
  - Markdown summaries
- because free-tier Gemini rate limits are tight, generation-based scoring can also be run on a paced representative subset using:
  - `EVAL_ENABLE_GENERATION=true`
  - `EVAL_EXPERIMENTS=...`
  - `EVAL_CASE_IDS=...`
  - `EVAL_GENERATION_MIN_INTERVAL_SECONDS=...`

Run the benchmark with:

```bash
python backend/eval.py
```

Set `EVAL_ENABLE_GENERATION=true` when you want to include answer-generation scoring and your Gemini quota is available.

## Current Results

Latest retrieval-only benchmark results are based on:

- `26` tuned questions
- `8` blind questions
- `34` total cases across Apple, Microsoft, and Nvidia

Best current configuration:

- company filter plus filing-type filter
- `top-k = 3`
- section-aware weighted intent routing

Latest measured result on the most recent internal benchmark run:

- `100%` overall top-1 section hit rate on the full `34`-question benchmark
- `100%` top-1 section hit rate on both the `tuned` and `blind` splits under the best configuration
- `38.89 ms` average retrieval latency for the best metadata-filtered configuration
- `31.14 ms` average retrieval latency for the company-only `top-k=3` configuration
- `1807` chunks indexed from `6` SEC filings across Apple, Microsoft, and Nvidia

Generation-based scoring on a paced 6-case subset of the strongest configuration (`company + filing_type + top-k=3`) produced:

- `100%` section hit rate and `100%` top-1 section hit rate on the subset
- `0.7667` average keyword coverage in generated answers
- `4.47 s` average generation time
- stronger coverage on the two blind cases in the subset (`0.9`) than on the four standard cases (`0.7`)

The benchmark also captured a useful failure mode during iteration:

- an earlier heuristic version reached `100%` on the tuned split but only `62.5%` on the blind split
- targeted weighted phrase routing then lifted the blind split from `62.5%` to `100%` without materially increasing latency
- a parser fix that restored `mda` content in `10-Q` filings then lifted `company + filing_type + top-k=3` retrieval from `64.71%` to `100%`
- generation scoring showed that retrieval can still be correct while answer quality varies, especially when the retrieved quarterly `mda` chunks are introductory rather than detail-rich

These are strong internal results, but the generation numbers should be interpreted as a subset-based grounded-answer check rather than a full answer-quality benchmark over all `34` cases.

## Current Limitation

The biggest quarterly-filings gap is now resolved:

- the parser now restores `mda` sections for the tracked `10-Q` filings
- rebuilding the vector store after that parser fix closed the main performance gap in filing-filtered retrieval

There is still some cleanup left in quarterly `risk_factors` extraction. Some `10-Q` risk-factor sections begin from less-than-ideal boundaries, so the parser can be tightened further even though the benchmark now retrieves the expected sections correctly.

There is also a chunk-quality limitation inside some quarterly `mda` retrieval results. For example, the system can retrieve the correct `mda` section for an Nvidia quarterly question, but still generate a weak answer if the top chunks are mostly introductory language instead of the more detailed operating discussion.

This is a good example of a real RAG lesson from the project: retrieval quality is often constrained as much by parsing and data quality as by ranking logic.

## Key Insights

The most important lessons from the project so far are:

- retrieval quality improved the most when the corpus improved, not when the prompt changed
- metadata filtering only became reliable after the parser restored quarterly `mda` sections
- weighted section routing helped a lot in this domain because SEC questions often map cleanly to stable sections
- perfect section retrieval does not guarantee perfect answers; chunk quality and excerpt specificity still matter
- evaluation needs multiple layers: retrieval placement, blind-query robustness, and grounded answer quality

## What This Project Demonstrates

This repo is meant to show more than "chat with documents." It demonstrates:

- section-aware ingestion of long-form SEC filings
- metadata-rich retrieval over `10-K` and `10-Q` documents
- retrieval experiments across filtering and `top-k` settings
- benchmark-driven iteration on retrieval quality
- frontend evidence display and latency instrumentation

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
