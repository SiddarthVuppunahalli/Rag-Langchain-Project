from __future__ import annotations

import csv
import datetime as dt
import json
from statistics import mean
from time import perf_counter

from config import EVAL_RESULTS_DIR
from rag_pipeline import get_rag_pipeline


BENCHMARK_QUESTIONS = [
    {
        "question": "What risks does the company describe around supply chain or manufacturing concentration?",
        "company": "AAPL",
        "filing_type": "10-K",
        "expected_sections": ["risk_factors", "business"],
    },
    {
        "question": "How does the company discuss AI-related demand or product strategy?",
        "company": "NVDA",
        "filing_type": "10-Q",
        "expected_sections": ["mda", "business"],
    },
    {
        "question": "What management commentary is provided about recent operating performance?",
        "company": "MSFT",
        "filing_type": "10-Q",
        "expected_sections": ["mda"],
    },
]


def evaluate_retrieval() -> tuple[list[dict], dict]:
    pipeline = get_rag_pipeline()
    rows: list[dict] = []
    latencies_ms: list[float] = []
    section_hit_flags: list[int] = []

    for item in BENCHMARK_QUESTIONS:
        started_at = perf_counter()
        result = pipeline.answer(
            question=item["question"],
            company=item["company"],
            filing_type=item["filing_type"],
        )
        latency_ms = (perf_counter() - started_at) * 1000
        latencies_ms.append(latency_ms)

        retrieved_sections = [doc.metadata.get("section") for doc in result["context"]]
        section_hit = int(any(section in item["expected_sections"] for section in retrieved_sections))
        section_hit_flags.append(section_hit)

        rows.append(
            {
                "question": item["question"],
                "company": item["company"],
                "filing_type": item["filing_type"],
                "retrieval_count": result["retrieval_count"],
                "latency_ms": round(latency_ms, 2),
                "retrieved_sections": retrieved_sections,
                "section_hit": section_hit,
                "answer_preview": result["answer"][:280],
            }
        )

    summary = {
        "questions_evaluated": len(BENCHMARK_QUESTIONS),
        "avg_latency_ms": round(mean(latencies_ms), 2) if latencies_ms else 0,
        "section_hit_rate": round(mean(section_hit_flags), 4) if section_hit_flags else 0,
        "avg_retrieval_count": round(mean(row["retrieval_count"] for row in rows), 2) if rows else 0,
    }
    return rows, summary


def save_results(rows: list[dict], summary: dict) -> None:
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    summary_path = EVAL_RESULTS_DIR / f"eval_summary_{timestamp}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    csv_path = EVAL_RESULTS_DIR / f"eval_rows_{timestamp}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    print("Evaluation complete.")
    print(json.dumps(summary, indent=2))
    print(f"Saved row-level results to: {csv_path}")
    print(f"Saved summary results to: {summary_path}")


def main() -> None:
    rows, summary = evaluate_retrieval()
    save_results(rows, summary)


if __name__ == "__main__":
    main()
