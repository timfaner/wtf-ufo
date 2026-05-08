#!/usr/bin/env python3
"""Merge embedded PDF text and OCR text into final page/document text outputs."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "data/extracted/pages.jsonl"
OCR_PAGES = ROOT / "data/extracted/ocr/ocr_pages.jsonl"
FINAL_DIR = ROOT / "data/extracted/final_text"
FINAL_PAGE_DIR = FINAL_DIR / "pages"


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
    return path.read_text(encoding="utf-8", errors="replace").strip()


def main() -> None:
    pages = read_jsonl(PAGES)
    ocr_by_page = {
        (row["record_id"], int(row["page"])): row
        for row in read_jsonl(OCR_PAGES)
        if row.get("status") == "ok"
    }

    final_rows: list[dict] = []
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for page in pages:
        key = (page["record_id"], int(page["page"]))
        embedded = read_text(page.get("text_path", ""))
        ocr = read_text(ocr_by_page.get(key, {}).get("ocr_text_path", ""))
        if embedded and ocr and ocr not in embedded:
            final_text = f"{embedded}\n\n[OCR]\n{ocr}"
            source = "embedded+ocr"
        elif embedded:
            final_text = embedded
            source = "embedded"
        else:
            final_text = ocr
            source = "ocr" if ocr else "empty"

        page_path = FINAL_PAGE_DIR / page["record_id"] / f"page_{int(page['page']):04d}.txt"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(final_text + ("\n" if final_text else ""), encoding="utf-8")
        row = {
            "record_id": page["record_id"],
            "title": page["title"],
            "page": int(page["page"]),
            "source": source,
            "embedded_text_chars": len(embedded),
            "ocr_text_chars": len(ocr),
            "final_text_chars": len(final_text),
            "final_text_path": str(page_path.relative_to(ROOT)),
        }
        final_rows.append(row)
        by_doc[page["record_id"]].append(row)

    doc_rows = []
    for record_id, rows in sorted(by_doc.items()):
        text_parts = []
        for row in sorted(rows, key=lambda item: item["page"]):
            text = read_text(row["final_text_path"])
            if text:
                text_parts.append(f"\n\n--- Page {row['page']} [{row['source']}] ---\n{text}")
        doc_path = FINAL_DIR / "documents" / f"{record_id}.txt"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("".join(text_parts).strip() + "\n", encoding="utf-8")
        doc_rows.append({
            "record_id": record_id,
            "pages": len(rows),
            "embedded_text_chars": sum(row["embedded_text_chars"] for row in rows),
            "ocr_text_chars": sum(row["ocr_text_chars"] for row in rows),
            "final_text_chars": sum(row["final_text_chars"] for row in rows),
            "final_text_path": str(doc_path.relative_to(ROOT)),
        })

    write_jsonl(FINAL_DIR / "pages.jsonl", final_rows)
    write_jsonl(FINAL_DIR / "documents.jsonl", doc_rows)
    (FINAL_DIR / "summary.md").write_text(
        "\n".join([
            "# Final Text Summary",
            "",
            f"- Pages: {len(final_rows)}",
            f"- Documents: {len(doc_rows)}",
            f"- Embedded text characters: {sum(row['embedded_text_chars'] for row in final_rows)}",
            f"- OCR text characters: {sum(row['ocr_text_chars'] for row in final_rows)}",
            f"- Final text characters: {sum(row['final_text_chars'] for row in final_rows)}",
        ]) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "pages": len(final_rows),
        "documents": len(doc_rows),
        "final_text_chars": sum(row["final_text_chars"] for row in final_rows),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

