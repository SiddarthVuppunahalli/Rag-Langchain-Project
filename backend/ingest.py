from __future__ import annotations

import json
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import (
    CHROMA_PATH,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_EMBEDDING_MODEL,
    PARSED_FILINGS_DIR,
)


def load_parsed_filings(parsed_dir: Path) -> list[dict]:
    filings: list[dict] = []
    for json_file in sorted(parsed_dir.glob("*/*/*.json")):
        filings.append(json.loads(json_file.read_text(encoding="utf-8")))
    return filings


def build_documents(parsed_filings: list[dict]) -> list[Document]:
    documents: list[Document] = []

    for filing in parsed_filings:
        ticker = filing["ticker"]
        filing_type = filing["filing_type"]
        filing_date = filing["filing_date"]
        accession_number = filing["accession_number"]

        for section_index, section in enumerate(filing["sections"]):
            metadata = {
                "ticker": ticker,
                "company": filing.get("company", ticker),
                "cik": filing.get("cik", ""),
                "filing_type": filing_type,
                "filing_date": filing_date,
                "accession_number": accession_number,
                "section": section["section"],
                "section_heading": section["heading"],
                "source_file": filing["source_file"],
                "source_url": filing.get("source_url", ""),
                "section_index": section_index,
            }
            documents.append(Document(page_content=section["content"], metadata=metadata))

    return documents


def chunk_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    for chunk_index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = (
            f"{chunk.metadata['ticker']}_{chunk.metadata['filing_type']}_"
            f"{chunk.metadata['filing_date']}_{chunk_index}"
        )
        chunk.metadata["chunk_index"] = chunk_index
        chunk.metadata["chunk_character_count"] = len(chunk.page_content)

    return chunks


def main() -> None:
    parsed_filings = load_parsed_filings(PARSED_FILINGS_DIR)
    if not parsed_filings:
        print("No parsed filings found. Run parse_filings.py first.")
        return

    documents = build_documents(parsed_filings)
    chunks = chunk_documents(documents)

    print(f"Parsed filings loaded: {len(parsed_filings)}")
    print(f"Section documents created: {len(documents)}")
    print(f"Chunks generated: {len(chunks)}")
    print(
        f"Chunking config: chunk_size={DEFAULT_CHUNK_SIZE}, "
        f"chunk_overlap={DEFAULT_CHUNK_OVERLAP}"
    )

    embeddings = HuggingFaceEmbeddings(model_name=DEFAULT_EMBEDDING_MODEL)
    print(f"Embedding model: {DEFAULT_EMBEDDING_MODEL}")
    print(f"Persisting vector store to: {CHROMA_PATH}")

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PATH),
    )

    print("Ingestion complete.")


if __name__ == "__main__":
    main()
