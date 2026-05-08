#!/usr/bin/env python3
"""Extract embedded text and images from downloaded PDF files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
PDF_MANIFEST = ROOT / "data/manifest/pdf_records.jsonl"
TEXT_DIR = ROOT / "data/extracted/text"
PAGE_DIR = ROOT / "data/extracted/pages"
IMAGE_DIR = ROOT / "data/extracted/images"
EXTRACTED_DIR = ROOT / "data/extracted"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)


def extract_pdf(record: dict, render_empty_pages: bool) -> tuple[dict, list[dict], list[dict]]:
    pdf_path = ROOT / record["local_path"]
    text_path = TEXT_DIR / f"{safe_name(record['id'])}.txt"
    doc_page_dir = PAGE_DIR / record["id"]
    doc_image_dir = IMAGE_DIR / record["id"]
    doc_summary = {
        "id": record["id"],
        "title": record["title"],
        "pdf_path": str(pdf_path.relative_to(ROOT)),
        "exists": pdf_path.exists(),
        "page_count": 0,
        "text_chars": 0,
        "image_count": 0,
        "status": "missing",
    }
    page_rows: list[dict] = []
    image_rows: list[dict] = []

    if not pdf_path.exists():
        return doc_summary, page_rows, image_rows

    existing_pages = sorted(doc_page_dir.glob("page_*.txt"))
    if text_path.exists() and existing_pages:
        existing_images = sorted(
            path for path in doc_image_dir.glob("**/*") if path.is_file() and not path.name.endswith("_render.png")
        )
        for page_file in existing_pages:
            page_number = int(page_file.stem.split("_")[-1])
            text = page_file.read_text(encoding="utf-8", errors="replace").strip()
            page_rows.append({
                "record_id": record["id"],
                "title": record["title"],
                "page": page_number,
                "text_chars": len(text),
                "text_path": str(page_file.relative_to(ROOT)),
                "embedded_image_count": 0,
                "image_paths": [],
                "rendered_page_path": "",
                "status": "reused",
            })
        for image_path in existing_images:
            image_rows.append({
                "record_id": record["id"],
                "title": record["title"],
                "page": 0,
                "image_index": 0,
                "path": str(image_path.relative_to(ROOT)),
                "status": "reused",
            })
        doc_summary.update({
            "page_count": len(existing_pages),
            "text_chars": len(text_path.read_text(encoding="utf-8", errors="replace")),
            "image_count": len(existing_images),
            "text_path": str(text_path.relative_to(ROOT)),
            "status": "ok",
            "reused": True,
        })
        return doc_summary, page_rows, image_rows

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:  # noqa: BLE001
        doc_summary["status"] = "open_error"
        doc_summary["error"] = str(exc)
        return doc_summary, page_rows, image_rows

    doc_text_parts: list[str] = []
    doc_page_dir.mkdir(parents=True, exist_ok=True)
    doc_image_dir.mkdir(parents=True, exist_ok=True)

    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        page_number = page_index + 1
        text = page.get_text("text").strip()
        page_text_path = doc_page_dir / f"page_{page_number:04d}.txt"
        page_text_path.write_text(text + ("\n" if text else ""), encoding="utf-8")
        if text:
            doc_text_parts.append(f"\n\n--- Page {page_number} ---\n{text}")

        page_images = page.get_images(full=True)
        extracted_images = []
        for image_index, image in enumerate(page_images, start=1):
            xref = image[0]
            try:
                image_info = doc.extract_image(xref)
            except Exception as exc:  # noqa: BLE001
                image_rows.append({
                    "record_id": record["id"],
                    "page": page_number,
                    "image_index": image_index,
                    "xref": xref,
                    "status": "extract_error",
                    "error": str(exc),
                })
                continue
            ext = image_info.get("ext", "bin")
            image_path = doc_image_dir / f"page_{page_number:04d}_image_{image_index:03d}_xref_{xref}.{ext}"
            image_path.write_bytes(image_info["image"])
            row = {
                "record_id": record["id"],
                "title": record["title"],
                "page": page_number,
                "image_index": image_index,
                "xref": xref,
                "width": image_info.get("width"),
                "height": image_info.get("height"),
                "colorspace": image_info.get("colorspace"),
                "extension": ext,
                "path": str(image_path.relative_to(ROOT)),
                "status": "ok",
            }
            image_rows.append(row)
            extracted_images.append(row["path"])

        rendered_path = ""
        if render_empty_pages and not text and not extracted_images:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            rendered = doc_image_dir / f"page_{page_number:04d}_render.png"
            pix.save(rendered)
            rendered_path = str(rendered.relative_to(ROOT))

        page_rows.append({
            "record_id": record["id"],
            "title": record["title"],
            "page": page_number,
            "text_chars": len(text),
            "text_path": str(page_text_path.relative_to(ROOT)),
            "embedded_image_count": len(page_images),
            "image_paths": extracted_images,
            "rendered_page_path": rendered_path,
        })

    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text("".join(doc_text_parts).strip() + "\n", encoding="utf-8")

    doc_summary.update({
        "page_count": doc.page_count,
        "text_chars": sum(row["text_chars"] for row in page_rows),
        "image_count": len([row for row in image_rows if row.get("status") == "ok"]),
        "text_path": str(text_path.relative_to(ROOT)),
        "status": "ok",
    })
    doc.close()
    return doc_summary, page_rows, image_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Limit number of PDFs for smoke testing.")
    parser.add_argument("--render-empty-pages", action="store_true", help="Render blank pages with no embedded text/images.")
    args = parser.parse_args()

    records = read_jsonl(PDF_MANIFEST)
    if args.limit:
        records = records[: args.limit]

    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    documents_count = 0
    available_documents = 0
    page_count = 0
    image_count = 0
    with (EXTRACTED_DIR / "documents.jsonl").open("w", encoding="utf-8") as summaries, \
        (EXTRACTED_DIR / "pages.jsonl").open("w", encoding="utf-8") as pages, \
        (EXTRACTED_DIR / "images.jsonl").open("w", encoding="utf-8") as images:
        for record in records:
            summary, page_rows, image_rows = extract_pdf(record, args.render_empty_pages)
            documents_count += 1
            available_documents += int(summary["status"] == "ok")
            page_count += len(page_rows)
            image_count += len([row for row in image_rows if row.get("status") in {"ok", "reused"}])
            summaries.write(json.dumps(summary, ensure_ascii=False, sort_keys=True) + "\n")
            for row in page_rows:
                pages.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            for row in image_rows:
                images.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            summaries.flush()
            pages.flush()
            images.flush()
            print(
                f"{summary['status']}: {record['id']} pages={summary['page_count']} "
                f"text={summary['text_chars']} images={summary['image_count']}",
                flush=True,
            )

    print(json.dumps({
        "documents": documents_count,
        "available_documents": available_documents,
        "pages": page_count,
        "images": image_count,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
