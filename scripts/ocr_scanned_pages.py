#!/usr/bin/env python3
"""OCR scanned PDF page images with macOS Vision."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "data/extracted/pages.jsonl"
IMAGES = ROOT / "data/extracted/images.jsonl"
OCR_DIR = ROOT / "data/extracted/ocr"
OCR_PAGES_DIR = OCR_DIR / "pages"
OCR_JSONL = OCR_DIR / "ocr_pages.jsonl"
SWIFT_SOURCE = ROOT / "scripts/vision_ocr.swift"
OCR_BIN = ROOT / ".venv/bin/vision_ocr"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def compile_ocr_tool() -> None:
    if OCR_BIN.exists() and OCR_BIN.stat().st_mtime >= SWIFT_SOURCE.stat().st_mtime:
        return
    OCR_BIN.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["swiftc", str(SWIFT_SOURCE), "-o", str(OCR_BIN)], check=True)


def existing_keys() -> set[tuple[str, int]]:
    keys: set[tuple[str, int]] = set()
    for row in read_jsonl(OCR_JSONL):
        if row.get("status") == "ok":
            keys.add((row["record_id"], int(row["page"])))
    return keys


def choose_page_images(images: list[dict]) -> dict[tuple[str, int], dict]:
    best: dict[tuple[str, int], dict] = {}
    for image in images:
        if image.get("status") != "ok":
            continue
        key = (image["record_id"], int(image["page"]))
        area = int(image.get("width") or 0) * int(image.get("height") or 0)
        current = best.get(key)
        current_area = int(current.get("width") or 0) * int(current.get("height") or 0) if current else -1
        if area > current_area:
            best[key] = image
    return best


def ocr_text_path(record_id: str, page: int) -> Path:
    return OCR_PAGES_DIR / record_id / f"page_{page:04d}_ocr.txt"


def make_jobs(text_threshold: int, force: bool, limit: int) -> list[dict]:
    pages = read_jsonl(PAGES)
    images = choose_page_images(read_jsonl(IMAGES))
    done = set() if force else existing_keys()
    jobs: list[dict] = []
    for page in pages:
        key = (page["record_id"], int(page["page"]))
        if key in done:
            continue
        if int(page.get("text_chars") or 0) > text_threshold:
            continue
        image = images.get(key)
        if not image:
            continue
        jobs.append({
            "record_id": page["record_id"],
            "title": page["title"],
            "page": int(page["page"]),
            "image_path": image["path"],
            "source_text_chars": int(page.get("text_chars") or 0),
        })
        if limit and len(jobs) >= limit:
            break
    return jobs


def run_batch(batch: list[dict], fast: bool) -> list[dict]:
    args = [str(OCR_BIN)]
    if fast:
        args.append("--fast")
    args.extend(str(ROOT / job["image_path"]) for job in batch)
    proc = subprocess.run(args, check=True, text=True, capture_output=True)
    by_path = {str(ROOT / job["image_path"]): job for job in batch}
    rows: list[dict] = []
    for line in proc.stdout.splitlines():
        result = json.loads(line)
        job = by_path[result["path"]]
        text_path = ocr_text_path(job["record_id"], job["page"])
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text = result.get("text", "")
        text_path.write_text(text + ("\n" if text else ""), encoding="utf-8")
        rows.append({
            **job,
            "status": result["status"],
            "confidence": result.get("confidence", 0),
            "ocr_text_chars": len(text),
            "ocr_text_path": str(text_path.relative_to(ROOT)),
            "error": result.get("error") or "",
        })
    return rows


def append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_summary() -> None:
    rows = read_jsonl(OCR_JSONL)
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_doc[row["record_id"]].append(row)
    docs = []
    for record_id, doc_rows in sorted(by_doc.items()):
        docs.append({
            "record_id": record_id,
            "ocr_pages": len(doc_rows),
            "ocr_text_chars": sum(int(row.get("ocr_text_chars") or 0) for row in doc_rows),
            "average_confidence": (
                sum(float(row.get("confidence") or 0) for row in doc_rows) / len(doc_rows)
                if doc_rows else 0
            ),
        })
    (OCR_DIR / "ocr_documents.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in docs),
        encoding="utf-8",
    )
    total_chars = sum(row["ocr_text_chars"] for row in docs)
    (OCR_DIR / "summary.md").write_text(
        "\n".join([
            "# OCR Summary",
            "",
            f"- OCR page rows: {len(rows)}",
            f"- OCR document rows: {len(docs)}",
            f"- OCR text characters: {total_chars}",
        ]) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-threshold", type=int, default=20, help="OCR pages with extracted text chars <= threshold.")
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()

    compile_ocr_tool()
    jobs = make_jobs(args.text_threshold, args.force, args.limit)
    print(json.dumps({"ocr_jobs": len(jobs), "text_threshold": args.text_threshold, "fast": args.fast}), flush=True)
    for start in range(0, len(jobs), args.batch_size):
        batch = jobs[start:start + args.batch_size]
        rows = run_batch(batch, args.fast)
        append_jsonl(OCR_JSONL, rows)
        done = start + len(batch)
        chars = sum(row["ocr_text_chars"] for row in rows)
        print(f"ocr batch {done}/{len(jobs)} pages={len(rows)} chars={chars}", flush=True)
    write_summary()


if __name__ == "__main__":
    main()

