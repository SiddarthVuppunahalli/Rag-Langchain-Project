from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path

from config import PARSED_FILINGS_DIR, RAW_FILINGS_DIR


SECTION_SPECS_BY_FILING_TYPE = {
    "10-K": [
        {
            "name": "business",
            "start_pattern": r"item\s+1\.*\s+business",
            "end_patterns": [r"item\s+1a\.*\s+risk\s+factors"],
        },
        {
            "name": "risk_factors",
            "start_pattern": r"item\s+1a\.*\s+risk\s+factors",
            "end_patterns": [r"item\s+1b\.*", r"item\s+2\.*"],
        },
        {
            "name": "mda",
            "start_pattern": r"item\s+7\.*\s+management(?:'|\u2019)?s\s+discussion\s+and\s+analysis",
            "end_patterns": [r"item\s+7a\.*", r"item\s+8\.*"],
        },
    ],
    "10-Q": [
        {
            "name": "mda",
            "start_pattern": r"item\s+2\.*\s+management(?:'|\u2019)?s\s+discussion\s+and\s+analysis",
            "end_patterns": [r"item\s+3\.*", r"item\s+4\.*", r"part\s+ii"],
            "selection_strategy": "latest_non_toc",
        },
        {
            "name": "risk_factors",
            "start_pattern": r"item\s+1a\.*\s+risk\s+factors",
            "end_patterns": [r"item\s+2\.*\s+unregistered", r"item\s+5\.*", r"item\s+6\.*"],
            "selection_strategy": "latest_non_toc",
        },
    ],
}

MIN_SECTION_SPAN = 1500


@dataclass
class ParsedSection:
    section: str
    heading: str
    content: str
    character_count: int
    word_count: int


def clean_filing_text(raw_text: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw_text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def looks_like_table_of_contents(candidate_text: str) -> bool:
    early_text = candidate_text[:300].lower()
    item_refs = re.findall(r"item\s+\d+[a-z]?\.*", early_text, flags=re.IGNORECASE)
    distinct_item_refs = set(item_refs)
    has_page_number_bridge = bool(re.search(r"\b\d{1,3}\s+item\s+\d", early_text, flags=re.IGNORECASE))
    return has_page_number_bridge or len(distinct_item_refs) >= 2 or len(item_refs) >= 3


def choose_candidate_span(
    candidates: list[tuple[int, int]],
    text: str,
    selection_strategy: str = "longest_non_toc",
) -> tuple[int, int] | None:
    if not candidates:
        return None

    non_toc_candidates = [
        span for span in candidates if not looks_like_table_of_contents(text[span[0]:span[1]])
    ]

    if selection_strategy == "latest_non_toc":
        if non_toc_candidates:
            return max(non_toc_candidates, key=lambda span: span[0])
        return max(candidates, key=lambda span: span[0])

    if non_toc_candidates:
        return max(non_toc_candidates, key=lambda span: span[1] - span[0])

    # SEC filings often repeat section headings in a table of contents near the top.
    # When every match looks TOC-like, fall back to the longest span we found.
    return max(candidates, key=lambda span: span[1] - span[0])


def find_section_span(
    text: str,
    start_pattern: str,
    end_patterns: list[str],
    selection_strategy: str = "longest_non_toc",
) -> tuple[int, int] | None:
    candidates: list[tuple[int, int]] = []
    for start_match in re.finditer(start_pattern, text, flags=re.IGNORECASE):
        start = start_match.start()
        end = len(text)

        for end_pattern in end_patterns:
            for end_match in re.finditer(end_pattern, text, flags=re.IGNORECASE):
                if end_match.start() <= start_match.end():
                    continue
                if end_match.start() - start < MIN_SECTION_SPAN:
                    continue
                end = min(end, end_match.start())
                break

        if end <= start:
            continue
        candidates.append((start, end))

    return choose_candidate_span(candidates, text, selection_strategy=selection_strategy)


def extract_sections(clean_text: str, filing_type: str) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    section_specs = SECTION_SPECS_BY_FILING_TYPE.get(filing_type, [])
    for section_spec in section_specs:
        span = find_section_span(
            clean_text,
            section_spec["start_pattern"],
            section_spec["end_patterns"],
            selection_strategy=section_spec.get("selection_strategy", "longest_non_toc"),
        )
        if not span:
            continue

        start, end = span
        content = clean_text[start:end].strip()
        heading_text = " ".join(content.split(" ", 8)[:8])
        sections.append(
            ParsedSection(
                section=section_spec["name"],
                heading=heading_text,
                content=content,
                character_count=len(content),
                word_count=len(content.split()),
            )
        )
    return sections


def parse_filing_file(filing_path: Path) -> dict:
    raw_text = filing_path.read_text(encoding="utf-8", errors="ignore")
    clean_text = clean_filing_text(raw_text)

    path_parts = filing_path.parts
    ticker = path_parts[-3]
    filing_type = path_parts[-2]
    filing_id = filing_path.stem
    filing_date, accession_number = filing_id.split("_", 1)
    sections = extract_sections(clean_text, filing_type)

    return {
        "ticker": ticker,
        "filing_type": filing_type,
        "filing_date": filing_date,
        "accession_number": accession_number,
        "source_file": str(filing_path),
        "raw_character_count": len(raw_text),
        "clean_character_count": len(clean_text),
        "section_count": len(sections),
        "sections": [asdict(section) for section in sections],
    }


def load_manifest_lookup() -> dict[tuple[str, str], dict]:
    manifest_path = RAW_FILINGS_DIR / "manifest.json"
    if not manifest_path.exists():
        return {}

    manifest_rows = json.loads(manifest_path.read_text(encoding="utf-8"))
    lookup: dict[tuple[str, str], dict] = {}
    for row in manifest_rows:
        lookup[(row["ticker"], row["accession_number"])] = row
    return lookup


def main() -> None:
    PARSED_FILINGS_DIR.mkdir(parents=True, exist_ok=True)

    filing_files = sorted(RAW_FILINGS_DIR.glob("*/*/*.html"))
    manifest_lookup = load_manifest_lookup()
    parsed_count = 0
    total_sections = 0

    for filing_file in filing_files:
        parsed = parse_filing_file(filing_file)
        manifest_row = manifest_lookup.get((parsed["ticker"], parsed["accession_number"]))
        if manifest_row:
            parsed["company"] = manifest_row["company"]
            parsed["cik"] = manifest_row["cik"]
            parsed["source_url"] = manifest_row["source_url"]
        total_sections += parsed["section_count"]

        output_dir = PARSED_FILINGS_DIR / parsed["ticker"] / parsed["filing_type"]
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{parsed['filing_date']}_{parsed['accession_number']}.json"
        output_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        parsed_count += 1

        print(
            f"Parsed {parsed['ticker']} {parsed['filing_type']} {parsed['filing_date']} "
            f"into {parsed['section_count']} tracked sections"
        )

    print("\nParse complete.")
    print(f"Filings parsed: {parsed_count}")
    print(f"Tracked sections extracted: {total_sections}")


if __name__ == "__main__":
    main()
