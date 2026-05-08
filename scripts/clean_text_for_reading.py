#!/usr/bin/env python3
"""Create readable and searchable text layers from merged PDF/OCR text."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifest/records.jsonl"
FINAL_PAGES = ROOT / "data/extracted/final_text/pages.jsonl"
CURATED = ROOT / "data/curated"
READABLE_DOCS = CURATED / "readable" / "documents"
READABLE_PAGES = CURATED / "readable" / "pages"
VERBATIM_PAGES = CURATED / "verbatim" / "pages"
SEARCH = CURATED / "search"
LLM_READY = CURATED / "llm_ready"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_text(relative_path: str) -> str:
    if not relative_path:
        return ""
    path = ROOT / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "untitled"


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    text = text.replace("\u00ad", "")
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def canonical_line(line: str) -> str:
    line = normalize_text(line).strip().lower()
    line = re.sub(r"\s+", " ", line)
    return line


def is_probable_boilerplate(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 110:
        return False
    if re.fullmatch(r"\d{1,4}", stripped):
        return True
    if re.search(r"\b(page|p\.)\s*\d+\b", stripped, re.I):
        return True
    if re.search(r"\b(contract|report|task|section|serial|document|distribution)\b", stripped, re.I):
        return True
    if re.search(r"\b(secret|confidential|unclassified|for official use only|released under)\b", stripped, re.I):
        return True
    if re.search(r"\b\d{2,4}[-/][A-Z0-9][A-Z0-9\-/]{2,}\b", stripped, re.I):
        return True
    if stripped.isupper() and len(stripped.split()) <= 8:
        return True
    return False


def is_artifact_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) <= 1:
        return True
    alnum = sum(ch.isalnum() for ch in stripped)
    if alnum == 0 and len(stripped) >= 3:
        return True
    if len(stripped) >= 6 and alnum / len(stripped) < 0.18:
        return True
    if re.fullmatch(r"[-_=~*.,;: /\[\](){}<>|\\]+", stripped):
        return True
    if re.fullmatch(r"(.)\1{5,}", stripped):
        return True
    return False


def is_low_value_short_line(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) > 5:
        return False
    if re.fullmatch(r"[A-Za-z]{1,2}", stripped):
        return True
    if re.fullmatch(r"\d{1,2}", stripped):
        return True
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.,:-]{0,4}", stripped) and not any(ch.islower() for ch in stripped):
        return True
    return False


def likely_table_or_code(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) <= 3:
        return True
    alnum = sum(ch.isalnum() for ch in stripped)
    if alnum and len(stripped) / max(alnum, 1) > 2.8:
        return True
    if re.fullmatch(r"[A-Z0-9/.,:;#\-() \[\]]{1,32}", stripped) and len(stripped.split()) <= 5:
        return True
    return False


def likely_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith(("SECRET", "CONFIDENTIAL", "UNCLASSIFIED")):
        return True
    if len(stripped) <= 72 and stripped.isupper() and len(stripped.split()) <= 10:
        return True
    if re.match(r"^(Form Approved|REPORT DOCUMENTATION PAGE|Abstract|NOTE:|SUBJECT:)", stripped, re.I):
        return True
    return False


def starts_structural_line(line: str) -> bool:
    stripped = line.strip()
    return bool(
        re.match(r"^([A-Z]\.|[0-9]+\.|[-*•]|\([a-z0-9]+\))\s+", stripped, re.I)
        or re.match(r"^(From|To|Subject|Date|Dear|Sincerely|At \d{3,4} hours)\b", stripped, re.I)
    )


def should_join(prev: str, current: str) -> bool:
    prev = prev.rstrip()
    current = current.lstrip()
    if not prev or not current:
        return False
    if likely_heading(prev) or likely_heading(current):
        return False
    if likely_table_or_code(prev) or likely_table_or_code(current):
        return False
    if starts_structural_line(current):
        return False
    if prev.endswith((".", "?", "!", ":", ";", '"', "]", ")")):
        return False
    if len(prev) < 18 and len(current) < 32:
        return False
    if current[:1].islower():
        return True
    if len(prev) > 45 and len(current) > 20:
        return True
    return False


def preprocess_lines(text: str, repeated_lines: set[str]) -> tuple[list[str], Counter]:
    text = normalize_text(text)
    raw_lines = [line.strip() for line in text.split("\n")]
    lines: list[str] = []
    actions: Counter = Counter()
    skip_next = False
    previous_kept = ""
    for idx, line in enumerate(raw_lines):
        if skip_next:
            skip_next = False
            continue
        if not line:
            lines.append("")
            previous_kept = ""
            continue
        if canonical_line(line) in repeated_lines:
            actions["removed_repeated_boilerplate_lines"] += 1
            continue
        if is_artifact_line(line):
            actions["removed_artifact_lines"] += 1
            continue
        if is_low_value_short_line(line):
            actions["removed_low_value_short_lines"] += 1
            continue
        if previous_kept and canonical_line(previous_kept) == canonical_line(line):
            actions["removed_adjacent_duplicate_lines"] += 1
            continue
        if line.endswith("-") and idx + 1 < len(raw_lines):
            nxt = raw_lines[idx + 1].strip()
            if nxt and nxt[:1].islower():
                lines.append(line[:-1] + nxt)
                previous_kept = line[:-1] + nxt
                skip_next = True
                actions["repaired_hyphenated_line_breaks"] += 1
                continue
        lines.append(line)
        previous_kept = line
    return lines, actions


def clean_page_text(text: str, repeated_lines: set[str] | None = None) -> tuple[str, dict[str, int]]:
    lines, actions = preprocess_lines(text, repeated_lines or set())

    paragraphs: list[str] = []
    current = ""
    for line in lines:
        if not line:
            if current:
                paragraphs.append(current.strip())
                current = ""
            continue
        if not current:
            current = line
            continue
        if should_join(current, line):
            current = f"{current} {line}"
            actions["joined_wrapped_lines"] += 1
        else:
            paragraphs.append(current.strip())
            current = line
    if current:
        paragraphs.append(current.strip())

    cleaned = "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip(), dict(actions)


def document_repeated_lines(pages: list[dict]) -> dict[str, set[str]]:
    page_counts: dict[str, int] = Counter(page["record_id"] for page in pages)
    line_counts: dict[str, Counter] = defaultdict(Counter)
    seen_per_page: set[tuple[str, int, str]] = set()
    for page in pages:
        text = read_text(page["final_text_path"])
        for line in normalize_text(text).splitlines():
            stripped = line.strip()
            if not is_probable_boilerplate(stripped):
                continue
            key = canonical_line(stripped)
            if not key:
                continue
            seen_key = (page["record_id"], int(page["page"]), key)
            if seen_key in seen_per_page:
                continue
            seen_per_page.add(seen_key)
            line_counts[page["record_id"]][key] += 1

    repeated: dict[str, set[str]] = {}
    for record_id, counts in line_counts.items():
        threshold = 3 if page_counts[record_id] < 16 else max(4, int(page_counts[record_id] * 0.18))
        repeated[record_id] = {line for line, count in counts.items() if count >= threshold}
    return repeated


def chunk_text(text: str, max_chars: int = 1800, overlap: int = 180) -> list[str]:
    text = text.strip()
    if not text:
        return []
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= max_chars:
            current = paragraph
        else:
            start = 0
            while start < len(paragraph):
                chunks.append(paragraph[start:start + max_chars])
                start += max_chars - overlap
            current = ""
    if current:
        chunks.append(current)
    return chunks


def text_stats(text: str) -> dict[str, int | float]:
    tokens = re.findall(r"\S+", text)
    alpha_words = re.findall(r"[A-Za-z][A-Za-z']{2,}", text)
    vowel_words = [word for word in alpha_words if re.search(r"[aeiouyAEIOUY]", word)]
    sentence_like_blocks = 0
    for block in re.split(r"\n{2,}", text):
        words = re.findall(r"[A-Za-z][A-Za-z']{2,}", block)
        if len(words) >= 8 and re.search(r"[.!?;:]$", block.strip()):
            sentence_like_blocks += 1
    return {
        "token_count": len(tokens),
        "alpha_word_count": len(alpha_words),
        "natural_language_score": round(len(vowel_words) / max(len(tokens), 1), 3),
        "sentence_like_blocks": sentence_like_blocks,
        "line_count": len([line for line in text.splitlines() if line.strip()]),
    }


def quality_score(raw_chars: int, clean_chars: int, actions: dict[str, int], stats: dict[str, int | float]) -> str:
    if raw_chars == 0 or clean_chars == 0:
        return "empty"
    ratio = clean_chars / raw_chars
    removals = sum(value for key, value in actions.items() if key.startswith("removed_"))
    if clean_chars < 320 and stats["sentence_like_blocks"] == 0 and stats["alpha_word_count"] < 28:
        return "needs_review"
    if stats["natural_language_score"] < 0.18 and stats["sentence_like_blocks"] == 0:
        return "needs_review"
    if ratio < 0.18 or removals > 40:
        return "needs_review"
    if ratio < 0.45:
        return "aggressive_cleanup"
    return "clean"


def include_in_default_rag(cleaned: str, quality: str, stats: dict[str, int | float]) -> bool:
    if quality in {"empty", "needs_review"}:
        return False
    if len(cleaned) < 180:
        return False
    if re.search(r"\b(UFO|UAP|flying saucers?|flying discs?|flying disks?|orbs?|unidentified)\b", cleaned, re.I):
        return stats["natural_language_score"] >= 0.28 and stats["alpha_word_count"] >= 12
    if stats["sentence_like_blocks"] >= 1:
        return True
    if stats["natural_language_score"] >= 0.32 and stats["alpha_word_count"] >= 80:
        return True
    return False


def markdown_header(record: dict) -> str:
    fields = [
        f"# {record['title']}",
        "",
        f"- Record ID: `{record['id']}`",
        f"- Agency: {record.get('agency') or 'N/A'}",
        f"- Release date: {record.get('release_date') or 'N/A'}",
        f"- Incident date: {record.get('incident_date') or 'N/A'}",
        f"- Incident location: {record.get('incident_location') or 'N/A'}",
        f"- Source URL: {record.get('source_url') or 'N/A'}",
    ]
    if record.get("description"):
        fields.extend(["", "## Official Description", "", record["description"]])
    return "\n".join(fields).strip() + "\n"


def main() -> None:
    records = {row["id"]: row for row in read_jsonl(MANIFEST)}
    pages = read_jsonl(FINAL_PAGES)
    repeated_by_doc = document_repeated_lines(pages)
    by_doc: dict[str, list[dict]] = defaultdict(list)
    READABLE_DOCS.mkdir(parents=True, exist_ok=True)
    READABLE_PAGES.mkdir(parents=True, exist_ok=True)
    VERBATIM_PAGES.mkdir(parents=True, exist_ok=True)
    SEARCH.mkdir(parents=True, exist_ok=True)
    LLM_READY.mkdir(parents=True, exist_ok=True)

    page_index_rows: list[dict] = []
    chunk_rows: list[dict] = []
    default_chunk_rows: list[dict] = []
    excluded_chunk_rows: list[dict] = []
    doc_index_rows: list[dict] = []

    for page in pages:
        text = read_text(page["final_text_path"])
        normalized_verbatim = normalize_text(text).strip()
        repeated_lines = repeated_by_doc.get(page["record_id"], set())
        cleaned, actions = clean_page_text(text, repeated_lines)
        readable_page = READABLE_PAGES / page["record_id"] / f"page_{int(page['page']):04d}.md"
        readable_page.parent.mkdir(parents=True, exist_ok=True)
        readable_page.write_text(cleaned + ("\n" if cleaned else ""), encoding="utf-8")
        verbatim_page = VERBATIM_PAGES / page["record_id"] / f"page_{int(page['page']):04d}.txt"
        verbatim_page.parent.mkdir(parents=True, exist_ok=True)
        verbatim_page.write_text(normalized_verbatim + ("\n" if normalized_verbatim else ""), encoding="utf-8")
        stats = text_stats(cleaned)
        quality = quality_score(page["final_text_chars"], len(cleaned), actions, stats)
        include_default = include_in_default_rag(cleaned, quality, stats)
        row = {
            "record_id": page["record_id"],
            "title": page["title"],
            "page": int(page["page"]),
            "source": page["source"],
            "embedded_text_chars": page["embedded_text_chars"],
            "ocr_text_chars": page["ocr_text_chars"],
            "raw_text_chars": page["final_text_chars"],
            "clean_text_chars": len(cleaned),
            "quality": quality,
            "include_in_default_rag": include_default,
            **stats,
            "cleaning_actions": actions,
            "verbatim_page_path": str(verbatim_page.relative_to(ROOT)),
            "readable_page_path": str(readable_page.relative_to(ROOT)),
        }
        page_index_rows.append(row)
        by_doc[page["record_id"]].append({**row, "cleaned": cleaned})

        for idx, chunk in enumerate(chunk_text(cleaned), start=1):
            chunk_stats = text_stats(chunk)
            chunk_row = {
                "chunk_id": f"{page['record_id']}:p{int(page['page']):04d}:c{idx:03d}",
                "record_id": page["record_id"],
                "title": page["title"],
                "page": int(page["page"]),
                "source": page["source"],
                "quality": quality,
                "include_in_default_rag": include_default,
                **chunk_stats,
                "text": chunk,
                "text_chars": len(chunk),
                "readable_page_path": str(readable_page.relative_to(ROOT)),
                "verbatim_page_path": str(verbatim_page.relative_to(ROOT)),
            }
            chunk_rows.append(chunk_row)
            if include_default:
                default_chunk_rows.append(chunk_row)
            else:
                excluded_chunk_rows.append(chunk_row)

    for record_id, doc_pages in sorted(by_doc.items()):
        record = records.get(record_id, {"id": record_id, "title": record_id})
        doc_parts = [markdown_header(record)]
        for page in sorted(doc_pages, key=lambda item: item["page"]):
            if page["cleaned"]:
                doc_parts.append(f"\n## Page {page['page']} ({page['source']})\n\n{page['cleaned']}\n")
        readable_doc = READABLE_DOCS / f"{safe_filename(record_id)}.md"
        readable_doc.write_text("\n".join(doc_parts).strip() + "\n", encoding="utf-8")
        doc_index_rows.append({
            "record_id": record_id,
            "title": record.get("title", record_id),
            "pages": len(doc_pages),
            "raw_text_chars": sum(page["raw_text_chars"] for page in doc_pages),
            "clean_text_chars": sum(page["clean_text_chars"] for page in doc_pages),
            "quality_counts": dict(Counter(page["quality"] for page in doc_pages)),
            "readable_doc_path": str(readable_doc.relative_to(ROOT)),
        })

    write_jsonl(CURATED / "readable" / "documents.jsonl", doc_index_rows)
    write_jsonl(CURATED / "readable" / "pages.jsonl", page_index_rows)
    write_jsonl(SEARCH / "pages.jsonl", page_index_rows)
    write_jsonl(SEARCH / "chunks.jsonl", chunk_rows)
    write_jsonl(SEARCH / "chunks_default.jsonl", default_chunk_rows)
    write_jsonl(SEARCH / "chunks_excluded.jsonl", excluded_chunk_rows)
    write_jsonl(LLM_READY / "chunks.jsonl", default_chunk_rows)
    (CURATED / "summary.md").write_text(
        "\n".join([
            "# Curated Text Summary",
            "",
            f"- Documents: {len(doc_index_rows)}",
            f"- Pages: {len(page_index_rows)}",
            f"- Search chunks: {len(chunk_rows)}",
            f"- Default LLM/RAG chunks: {len(default_chunk_rows)}",
            f"- Excluded/noisy chunks retained for audit: {len(excluded_chunk_rows)}",
            f"- Raw text characters: {sum(row['raw_text_chars'] for row in doc_index_rows)}",
            f"- Clean text characters: {sum(row['clean_text_chars'] for row in doc_index_rows)}",
            "",
            "Cleaning method: document-level boilerplate detection, OCR/control-character normalization, punctuation-artifact removal, low-value OCR fragment filtering, hyphenated-line repair, wrapped-line paragraph joining, Markdown page structure, and retrieval chunks with page-level provenance.",
            "",
            "`data/curated/search/chunks.jsonl` keeps every cleaned chunk. `data/curated/search/chunks_default.jsonl` and `data/curated/llm_ready/chunks.jsonl` are the cleaner default corpus for LLM/RAG use; they exclude empty pages, stamp-only pages, and pages flagged as likely OCR noise while retaining provenance back to readable and verbatim pages.",
            "",
            "Original extracted text remains under `data/extracted/final_text/`. Normalized verbatim page text is also written under `data/curated/verbatim/pages/` so the cleaner LLM/search layer can be audited against the evidence layer.",
        ]) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "documents": len(doc_index_rows),
        "pages": len(page_index_rows),
        "chunks": len(chunk_rows),
        "default_chunks": len(default_chunk_rows),
        "clean_text_chars": sum(row["clean_text_chars"] for row in doc_index_rows),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
