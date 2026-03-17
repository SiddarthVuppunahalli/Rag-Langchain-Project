"""
Phase 6: RAG Evaluation Script using RAGAS
===========================================
Evaluates the IT Helpdesk RAG pipeline across four key metrics:
  - Faithfulness:       Does the answer stay faithful to the retrieved context?
  - Answer Relevancy:   Is the answer relevant to the question asked?
  - Context Precision:  Are the retrieved chunks actually useful (signal-to-noise)?
  - Context Recall:     Do the retrieved chunks cover the ground truth answer?

Usage:
  # From the Rag-Langchain-Project root, with the venv active:
  python -m backend.eval

  # Or directly from the backend/ directory:
  cd backend && python eval.py
"""

import os
import sys
import json
import datetime
import pandas as pd
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 1.  Environment Setup
# ---------------------------------------------------------------------------
# Allow running as `python eval.py` from inside backend/ OR as
# `python -m backend.eval` from the project root.
_backend_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_backend_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

load_dotenv(os.path.join(_backend_dir, ".env"))

# ---------------------------------------------------------------------------
# 2.  Evaluation Dataset
#     Format: list of dicts with "question" and "ground_truth"
#     These cover the five IT documents downloaded in Phase 1.
# ---------------------------------------------------------------------------
EVAL_DATASET = [
    # -- ping.md --
    {
        "question": "How do I use the ping command to test network connectivity?",
        "ground_truth": (
            "You can use the ping command by typing 'ping <hostname_or_IP>' in the command prompt. "
            "It sends ICMP echo requests to the target host and displays the round-trip time "
            "to verify network connectivity and name resolution."
        ),
    },
    {
        "question": "What does the -t flag do in the ping command?",
        "ground_truth": (
            "The -t flag makes ping continuously send packets to the specified host until "
            "stopped manually with Ctrl+C, instead of the default four packets."
        ),
    },
    # -- ipconfig.md --
    {
        "question": "How can I view my current IP address on Windows?",
        "ground_truth": (
            "Run 'ipconfig' in the command prompt. It displays the IPv4 address, subnet mask, "
            "and default gateway for each network adapter on the system."
        ),
    },
    {
        "question": "What does 'ipconfig /flushdns' do?",
        "ground_truth": (
            "'ipconfig /flushdns' clears the DNS resolver cache, removing all cached DNS entries "
            "and forcing Windows to perform fresh DNS lookups for future requests."
        ),
    },
    # -- tracert.md --
    {
        "question": "What is the tracert command used for?",
        "ground_truth": (
            "tracert (Trace Route) is used to trace the path that packets take from your computer "
            "to a destination host. It shows each intermediate hop (router) along the route, "
            "along with the round-trip time to each hop, helping diagnose routing issues."
        ),
    },
    # -- nslookup.md --
    {
        "question": "How do I use nslookup to check DNS records for a domain?",
        "ground_truth": (
            "Run 'nslookup <domain>' at the command prompt. It queries the default DNS server "
            "and returns the IP address(es) associated with the domain, helping diagnose "
            "DNS resolution problems."
        ),
    },
    # -- net-use.md --
    {
        "question": "How do I map a network drive using the net use command?",
        "ground_truth": (
            "Use 'net use <drive_letter>: \\\\<server>\\<share>' to map a network share to a local "
            "drive letter. You can also supply credentials with '/user:<username>' and "
            "optionally '/persistent:yes' to reconnect at logon."
        ),
    },
    {
        "question": "How do I disconnect a mapped network drive with net use?",
        "ground_truth": (
            "Run 'net use <drive_letter>: /delete' to disconnect and remove a specific mapped "
            "drive. Use 'net use * /delete' to remove all current connections."
        ),
    },
]


# ---------------------------------------------------------------------------
# 3.  Build RAG pipeline and collect answers + contexts
# ---------------------------------------------------------------------------

def collect_rag_outputs(dataset: list[dict]) -> list[dict]:
    """Run each question through the RAG pipeline and collect answers + contexts."""
    print("\n[1/3] Loading RAG pipeline...")

    # Import here so failures give clear error messages
    try:
        from langchain_community.vectorstores import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain.chains import create_retrieval_chain
        from langchain.chains.combine_documents import create_stuff_documents_chain
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError as exc:
        print(f"\n[ERROR] Missing dependency: {exc}")
        print("Run: pip install -r backend/requirements.txt")
        sys.exit(1)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n[ERROR] GOOGLE_API_KEY not set. Add it to backend/.env")
        sys.exit(1)

    CHROMA_PATH = os.path.join(_backend_dir, "chroma_db")
    if not os.path.exists(CHROMA_PATH):
        print(f"\n[ERROR] ChromaDB not found at {CHROMA_PATH}.")
        print("Run backend ingestion first: python -m backend.ingest")
        sys.exit(1)

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    retriever = db.as_retriever(search_kwargs={"k": 3})

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)

    system_prompt = (
        "You are an IT Helpdesk AI Assistant. Use the following pieces of retrieved technical "
        "documentation to answer the user's question. If you don't know the answer or the context "
        "doesn't contain the answer, just say that you don't know, don't try to make up an answer."
        "\n\nContext:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    qa_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, qa_chain)

    print(f"[1/3] Pipeline ready. Running {len(dataset)} test questions...\n")

    results = []
    for i, item in enumerate(dataset, 1):
        question = item["question"]
        ground_truth = item["ground_truth"]
        print(f"  Q{i}/{len(dataset)}: {question[:70]}...")

        try:
            response = rag_chain.invoke({"input": question})
            answer = response.get("answer", "")
            context_docs = response.get("context", [])
            contexts = [doc.page_content for doc in context_docs]
        except Exception as exc:
            print(f"  [WARN] Failed for question {i}: {exc}")
            answer = ""
            contexts = []

        results.append({
            "question": question,
            "answer": answer,
            "contexts": contexts,
            "ground_truth": ground_truth,
        })

    return results


# ---------------------------------------------------------------------------
# 4.  Run RAGAS evaluation
# ---------------------------------------------------------------------------

def run_ragas_evaluation(results: list[dict]) -> pd.DataFrame:
    """Pass collected outputs through RAGAS and return a scored DataFrame."""
    print("[2/3] Running RAGAS evaluation metrics...")

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    except ImportError as exc:
        print(f"\n[ERROR] Missing dependency: {exc}")
        print("Run: pip install ragas datasets langchain-google-genai")
        sys.exit(1)

    # RAGAS expects a HuggingFace Dataset with specific column names
    ragas_data = {
        "question":     [r["question"]    for r in results],
        "answer":       [r["answer"]      for r in results],
        "contexts":     [r["contexts"]    for r in results],
        "ground_truth": [r["ground_truth"] for r in results],
    }
    dataset = Dataset.from_dict(ragas_data)

    api_key = os.getenv("GOOGLE_API_KEY")
    # Use Gemini as the judge LLM and embeddings for RAGAS
    judge_llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=api_key,
        temperature=0,
    )
    judge_embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key,
    )

    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=judge_llm,
        embeddings=judge_embeddings,
    )

    df = result.to_pandas()
    return df


# ---------------------------------------------------------------------------
# 5.  Display and save results
# ---------------------------------------------------------------------------

def display_and_save_results(df: pd.DataFrame) -> str:
    """Print a summary table and save detailed results to CSV."""
    print("\n[3/3] Evaluation complete.\n")

    # --- Summary statistics ---
    metric_cols = [c for c in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"] if c in df.columns]
    summary = df[metric_cols].describe().loc[["mean", "min", "max"]]

    print("=" * 65)
    print(" RAG Evaluation Summary (RAGAS Metrics)")
    print("=" * 65)
    print(summary.round(4).to_string())
    print("=" * 65)

    # --- Per-question results ---
    print("\nPer-question scores:")
    per_q = df[["question"] + metric_cols].copy()
    per_q["question"] = per_q["question"].str[:60] + "…"
    print(per_q.round(4).to_string(index=False))

    # --- Save to CSV ---
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(_project_root, "backend", "eval_results")
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, f"eval_{timestamp}.csv")

    # Save full data including answers
    save_cols = ["question", "answer", "ground_truth"] + metric_cols
    save_df = df[[c for c in save_cols if c in df.columns]]
    save_df.to_csv(csv_path, index=False)

    # Also save a JSON summary
    json_path = os.path.join(output_dir, f"eval_summary_{timestamp}.json")
    summary_dict = {
        "timestamp": timestamp,
        "num_questions": len(df),
        "metrics": {col: round(float(df[col].mean()), 4) for col in metric_cols},
    }
    with open(json_path, "w") as f:
        json.dump(summary_dict, f, indent=2)

    print(f"\n Results saved to:")
    print(f"   CSV:  {csv_path}")
    print(f"   JSON: {json_path}")
    return csv_path


# ---------------------------------------------------------------------------
# 6.  Main entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 65)
    print(" IT Helpdesk RAG — Phase 6 Evaluation (RAGAS)")
    print("=" * 65)
    print(f" Test dataset: {len(EVAL_DATASET)} questions")
    print(f" Metrics: faithfulness, answer_relevancy,")
    print(f"          context_precision, context_recall")
    print("=" * 65)

    # Step 1: Collect RAG answers and retrieved contexts
    results = collect_rag_outputs(EVAL_DATASET)

    # Step 2: Score with RAGAS
    df = run_ragas_evaluation(results)

    # Step 3: Display and persist
    display_and_save_results(df)

    print("\n Phase 6 evaluation complete!\n")


if __name__ == "__main__":
    main()
