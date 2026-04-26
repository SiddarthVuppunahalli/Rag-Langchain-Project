from __future__ import annotations

import json
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from config import RAW_FILINGS_DIR, SEC_USER_AGENT, TRACKED_COMPANIES, TRACKED_FILING_TYPES


SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"


@dataclass
class FilingRecord:
    ticker: str
    company: str
    cik: str
    filing_type: str
    filing_date: str
    accession_number: str
    primary_document: str
    source_url: str
    local_path: str


def sec_get_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": SEC_USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def sec_get_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": SEC_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,text/plain",
        },
    )
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8", errors="ignore")


def build_filing_url(cik: str, accession_number: str, primary_document: str) -> str:
    accession_no_dashes = accession_number.replace("-", "")
    cik_no_padding = str(int(cik))
    return f"{SEC_ARCHIVES_BASE}/{cik_no_padding}/{accession_no_dashes}/{primary_document}"


def fetch_company_filings(company_config, max_filings_per_type: int = 1) -> list[FilingRecord]:
    submission_url = SEC_SUBMISSIONS_URL.format(cik=company_config.cik)
    submission_data = sec_get_json(submission_url)
    recent = submission_data.get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_documents = recent.get("primaryDocument", [])

    fetched_records: list[FilingRecord] = []
    filing_counts: dict[str, int] = {filing_type: 0 for filing_type in TRACKED_FILING_TYPES}

    for form, filing_date, accession_number, primary_document in zip(
        forms,
        filing_dates,
        accession_numbers,
        primary_documents,
    ):
        if form not in TRACKED_FILING_TYPES:
            continue
        if filing_counts[form] >= max_filings_per_type:
            continue

        source_url = build_filing_url(company_config.cik, accession_number, primary_document)
        filing_dir = RAW_FILINGS_DIR / company_config.ticker / form
        filing_dir.mkdir(parents=True, exist_ok=True)
        local_path = filing_dir / f"{filing_date}_{accession_number}.html"

        print(f"Downloading {company_config.ticker} {form} filed on {filing_date}")
        local_path.write_text(sec_get_text(source_url), encoding="utf-8")

        fetched_records.append(
            FilingRecord(
                ticker=company_config.ticker,
                company=company_config.company,
                cik=company_config.cik,
                filing_type=form,
                filing_date=filing_date,
                accession_number=accession_number,
                primary_document=primary_document,
                source_url=source_url,
                local_path=str(local_path),
            )
        )
        filing_counts[form] += 1

    return fetched_records


def save_manifest(records: list[FilingRecord], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps([asdict(record) for record in records], indent=2),
        encoding="utf-8",
    )


def main() -> None:
    RAW_FILINGS_DIR.mkdir(parents=True, exist_ok=True)

    all_records: list[FilingRecord] = []
    for company_config in TRACKED_COMPANIES:
        records = fetch_company_filings(company_config)
        all_records.extend(records)

    manifest_path = RAW_FILINGS_DIR / "manifest.json"
    save_manifest(all_records, manifest_path)

    print("\nFetch complete.")
    print(f"Companies processed: {len(TRACKED_COMPANIES)}")
    print(f"Filings downloaded: {len(all_records)}")
    print(f"Manifest saved to: {manifest_path}")


if __name__ == "__main__":
    main()
