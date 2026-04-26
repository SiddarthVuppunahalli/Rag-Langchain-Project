# Frontend

This Next.js app provides the analyst-facing interface for the SEC filing RAG project.

## Purpose

The UI is meant to surface RAG behavior, not just accept a prompt. The current direction emphasizes:

- company and filing-type filters
- grounded answers from SEC documents
- visible evidence panels with filing metadata
- room for later metrics such as latency and retrieval diagnostics

## Local Run

```bash
npm install
npm run dev
```

Optional environment variable:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```
