from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
from pathlib import Path
from statistics import mean
from time import perf_counter

from config import BASE_DIR, DEFAULT_TOP_K, EVAL_RESULTS_DIR
from rag_pipeline import get_rag_pipeline


BENCHMARK_PATH = BASE_DIR / "benchmarks" / "sec_benchmark.json"
ENABLE_GENERATION_EVAL = os.getenv("EVAL_ENABLE_GENERATION", "false").lower() == "true"
MAX_CASES = int(os.getenv("EVAL_MAX_CASES", "0"))
EXPERIMENT_CONFIGS = [
    {
        "name": "company_and_filing_k3",
        "top_k": DEFAULT_TOP_K,
        "use_company_filter": True,
        "use_filing_type_filter": True,
    },
    {
        "name": "company_only_k3",
        "top_k": DEFAULT_TOP_K,
        "use_company_filter": True,
        "use_filing_type_filter": False,
    },
    {
        "name": "company_and_filing_k5",
        "top_k": 5,
        "use_company_filter": True,
        "use_filing_type_filter": True,
    },
]


def load_benchmark_cases(path: Path = BENCHMARK_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def keyword_coverage(answer: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 0.0

    normalized_answer = normalize_text(answer)
    hits = 0
    for keyword in expected_keywords:
        if normalize_text(keyword) in normalized_answer:
            hits += 1
    return hits / len(expected_keywords)


def evaluate_case(pipeline, case: dict, experiment: dict) -> dict:
    company = case["company"] if experiment["use_company_filter"] else None
    filing_type = case["filing_type"] if experiment["use_filing_type_filter"] else None

    retrieval_started_at = perf_counter()
    retrieved_documents = pipeline.retrieve(
        question=case["question"],
        company=company,
        filing_type=filing_type,
        top_k=experiment["top_k"],
    )
    retrieval_ms = round((perf_counter() - retrieval_started_at) * 1000, 2)
    retrieved_sections = [doc.metadata.get("section", "unknown") for doc in retrieved_documents]
    expected_sections = case.get("expected_sections", [])
    section_hit = int(any(section in expected_sections for section in retrieved_sections))
    top1_section_hit = int(bool(retrieved_sections) and retrieved_sections[0] in expected_sections)

    answer_preview = ""
    answer_keyword_score = 0.0
    generation_ms = 0.0
    total_ms = retrieval_ms
    context_characters = sum(len(doc.page_content) for doc in retrieved_documents)

    if ENABLE_GENERATION_EVAL:
        result = pipeline.answer(
            question=case["question"],
            company=company,
            filing_type=filing_type,
            top_k=experiment["top_k"],
        )
        answer_preview = result["answer"][:320]
        answer_keyword_score = keyword_coverage(result["answer"], case.get("expected_keywords", []))
        retrieval_ms = result["metrics"]["retrieval_ms"]
        generation_ms = result["metrics"]["generation_ms"]
        total_ms = result["metrics"]["total_ms"]
        context_characters = result["metrics"]["context_characters"]

    return {
        "experiment": experiment["name"],
        "case_id": case["id"],
        "difficulty": case.get("difficulty", "standard"),
        "company": case["company"],
        "expected_filing_type": case["filing_type"],
        "question": case["question"],
        "filters_company": company or "",
        "filters_filing_type": filing_type or "",
        "top_k": experiment["top_k"],
        "retrieval_count": len(retrieved_documents),
        "retrieved_sections": "|".join(retrieved_sections),
        "expected_sections": "|".join(expected_sections),
        "section_hit": section_hit,
        "top1_section_hit": top1_section_hit,
        "answer_keyword_coverage": round(answer_keyword_score, 4),
        "retrieval_ms": retrieval_ms,
        "generation_ms": generation_ms,
        "total_ms": total_ms,
        "context_characters": context_characters,
        "answer_preview": answer_preview,
    }


def summarize_rows(rows: list[dict]) -> dict:
    return {
        "questions_evaluated": len(rows),
        "avg_retrieval_count": round(mean(row["retrieval_count"] for row in rows), 2),
        "section_hit_rate": round(mean(row["section_hit"] for row in rows), 4),
        "top1_section_hit_rate": round(mean(row["top1_section_hit"] for row in rows), 4),
        "avg_answer_keyword_coverage": round(mean(row["answer_keyword_coverage"] for row in rows), 4),
        "avg_retrieval_ms": round(mean(row["retrieval_ms"] for row in rows), 2),
        "avg_generation_ms": round(mean(row["generation_ms"] for row in rows), 2),
        "avg_total_ms": round(mean(row["total_ms"] for row in rows), 2),
        "avg_context_characters": round(mean(row["context_characters"] for row in rows), 2),
    }


def summarize_experiment(rows: list[dict], experiment: dict) -> dict:
    summary = {
        "experiment": experiment["name"],
        "top_k": experiment["top_k"],
        "use_company_filter": experiment["use_company_filter"],
        "use_filing_type_filter": experiment["use_filing_type_filter"],
    }
    summary.update(summarize_rows(rows))

    by_difficulty: dict[str, dict] = {}
    for difficulty in sorted({row["difficulty"] for row in rows}):
        difficulty_rows = [row for row in rows if row["difficulty"] == difficulty]
        by_difficulty[difficulty] = summarize_rows(difficulty_rows)

    summary["by_difficulty"] = by_difficulty
    return summary


def run_experiments() -> tuple[list[dict], list[dict]]:
    benchmark_cases = load_benchmark_cases()
    if MAX_CASES > 0:
        benchmark_cases = benchmark_cases[:MAX_CASES]
    pipeline = get_rag_pipeline()

    all_rows: list[dict] = []
    summaries: list[dict] = []

    for experiment in EXPERIMENT_CONFIGS:
        experiment_rows = [evaluate_case(pipeline, case, experiment) for case in benchmark_cases]
        all_rows.extend(experiment_rows)
        summaries.append(summarize_experiment(experiment_rows, experiment))

    return all_rows, summaries


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)


def write_markdown_summary(path: Path, summaries: list[dict]) -> None:
    lines = [
        "# SEC RAG Evaluation Summary",
        "",
        "| Experiment | Top-k | Company Filter | Filing Filter | Section Hit | Top-1 Hit | Keyword Coverage | Avg Total ms | Avg Context Chars |",
        "| --- | ---: | :---: | :---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for summary in summaries:
        lines.append(
            "| {experiment} | {top_k} | {use_company_filter} | {use_filing_type_filter} | "
            "{section_hit_rate:.4f} | {top1_section_hit_rate:.4f} | {avg_answer_keyword_coverage:.4f} | "
            "{avg_total_ms:.2f} | {avg_context_characters:.2f} |".format(**summary)
        )
        lines.append("")
        lines.append(f"Difficulty breakdown for `{summary['experiment']}`:")
        lines.append("")
        lines.append("| Difficulty | Questions | Section Hit | Top-1 Hit | Avg Total ms |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for difficulty, difficulty_summary in summary["by_difficulty"].items():
            lines.append(
                f"| {difficulty} | {difficulty_summary['questions_evaluated']} | "
                f"{difficulty_summary['section_hit_rate']:.4f} | "
                f"{difficulty_summary['top1_section_hit_rate']:.4f} | "
                f"{difficulty_summary['avg_total_ms']:.2f} |"
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_results(rows: list[dict], summaries: list[dict]) -> None:
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    rows_path = EVAL_RESULTS_DIR / f"eval_rows_{timestamp}.csv"
    summary_json_path = EVAL_RESULTS_DIR / f"eval_summary_{timestamp}.json"
    summary_md_path = EVAL_RESULTS_DIR / f"eval_summary_{timestamp}.md"

    write_csv(rows_path, rows)
    summary_json_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    write_markdown_summary(summary_md_path, summaries)

    print("Evaluation complete.")
    print(json.dumps(summaries, indent=2))
    print(f"Generation-based answer scoring enabled: {ENABLE_GENERATION_EVAL}")
    print(f"Saved detailed rows to: {rows_path}")
    print(f"Saved JSON summary to: {summary_json_path}")
    print(f"Saved Markdown summary to: {summary_md_path}")


def main() -> None:
    rows, summaries = run_experiments()
    save_results(rows, summaries)


if __name__ == "__main__":
    main()
