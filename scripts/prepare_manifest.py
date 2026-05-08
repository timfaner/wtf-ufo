#!/usr/bin/env python3
"""Normalize the official PURSUE/UFO release CSV into project manifests."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = ROOT / "data/source/uap-csv.csv"
MANIFEST_DIR = ROOT / "data/manifest"


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\ufeff", " ")).strip()


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:120] or fallback


def basename_from_url(url: str, title: str, kind: str, index: int) -> str:
    parsed = urlparse(url)
    name = unquote(Path(parsed.path).name)
    if name and "." in name:
        return name
    ext = ".pdf" if kind == "PDF" else ".jpg" if kind == "IMG" else ""
    return f"{slugify(title, f'record-{index:03d}')}{ext}"


def local_path_for(kind: str, filename: str) -> str:
    if kind == "PDF":
        return f"data/raw/pdfs/{filename}"
    if kind == "IMG":
        return f"data/raw/images/{filename}"
    return ""


def repair_pdf_url(source_url: str, thumbnail_url: str) -> tuple[str, str]:
    if source_url.lower().endswith(".pdf"):
        return source_url, ""
    if not thumbnail_url:
        return source_url, "pdf_source_url_does_not_end_with_pdf"
    thumb_name = unquote(Path(urlparse(thumbnail_url).path).name)
    if not thumb_name.lower().endswith(".jpg"):
        return source_url, "pdf_source_url_does_not_end_with_pdf"
    repaired_name = thumb_name[:-4] + ".pdf"
    repaired = f"https://www.war.gov/medialink/ufo/release_1/{repaired_name}"
    return repaired, f"repaired_pdf_url_from_thumbnail:{source_url}"


def normalize_rows() -> list[dict]:
    rows: list[dict] = []
    with SOURCE_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            kind = clean(row.get("Type")).upper()
            title = clean(row.get("Title"))
            source_url = clean(row.get("PDF | Image Link"))
            thumbnail_url = clean(row.get("Modal Image"))
            repair_note = ""
            if kind == "PDF" and source_url and not source_url.lower().endswith(".pdf"):
                source_url, repair_note = repair_pdf_url(source_url, thumbnail_url)
            filename = basename_from_url(source_url, title, kind, index) if source_url else ""
            pdf_pairing = clean(row.get("PDF Pairing"))
            video_pairing = clean(row.get("Video Pairing"))
            record = {
                "id": f"release01-{index:04d}",
                "release": "release_1",
                "release_date": clean(row.get("Release Date")),
                "redaction": clean(row.get("Redaction")).upper() == "TRUE",
                "title": title,
                "kind": kind,
                "agency": clean(row.get("Agency")),
                "incident_date": clean(row.get("Incident Date")),
                "incident_location": clean(row.get("Incident Location")),
                "description": clean(row.get("Description Blurb")),
                "source_url": source_url,
                "thumbnail_url": thumbnail_url,
                "dvids_video_id": clean(row.get("DVIDS Video ID")),
                "video_title": clean(row.get("Video Title")),
                "pdf_pairing": pdf_pairing,
                "video_pairing": video_pairing,
                "filename": filename,
                "local_path": local_path_for(kind, filename),
                "slug": slugify(title, f"record-{index:03d}"),
            }
            if repair_note:
                record["repair"] = repair_note
            if kind == "PDF" and source_url and not source_url.lower().endswith(".pdf"):
                record["warning"] = "pdf_source_url_does_not_end_with_pdf"
            rows.append(record)
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    extras = sorted({key for row in rows for key in row.keys()} - set(fieldnames))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames + extras)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not SOURCE_CSV.exists():
        raise SystemExit(f"Missing source CSV: {SOURCE_CSV}")

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    rows = normalize_rows()
    pdfs = [row for row in rows if row["kind"] == "PDF"]
    images = [row for row in rows if row["kind"] == "IMG"]
    videos = [row for row in rows if row["kind"] == "VID"]

    write_jsonl(MANIFEST_DIR / "records.jsonl", rows)
    write_jsonl(MANIFEST_DIR / "pdf_records.jsonl", pdfs)
    write_jsonl(MANIFEST_DIR / "image_records.jsonl", images)
    write_jsonl(MANIFEST_DIR / "video_records.jsonl", videos)
    write_csv(MANIFEST_DIR / "records.csv", rows)

    (MANIFEST_DIR / "pdf_urls.txt").write_text(
        "\n".join(row["source_url"] for row in pdfs if row["source_url"]) + "\n",
        encoding="utf-8",
    )
    (MANIFEST_DIR / "image_urls.txt").write_text(
        "\n".join(row["source_url"] for row in images if row["source_url"]) + "\n",
        encoding="utf-8",
    )

    counts = Counter(row["kind"] for row in rows)
    warnings = [row for row in rows if row.get("warning")]
    repairs = [row for row in rows if row.get("repair")]
    summary = [
        "# PURSUE UFO Release 01 Manifest",
        "",
        f"- Source CSV: `{SOURCE_CSV.relative_to(ROOT)}`",
        f"- Total records: {len(rows)}",
        f"- PDF records: {counts.get('PDF', 0)}",
        f"- Image records: {counts.get('IMG', 0)}",
        f"- Video records: {counts.get('VID', 0)}",
        f"- Warning records: {len(warnings)}",
        f"- Repaired records: {len(repairs)}",
    ]
    if repairs:
        summary.append("")
        summary.append("## Repairs")
        for row in repairs:
            summary.append(f"- `{row['id']}` `{row['title']}`: {row['repair']} -> {row['source_url']}")
    if warnings:
        summary.append("")
        summary.append("## Warnings")
        for row in warnings:
            summary.append(f"- `{row['id']}` `{row['title']}`: {row['warning']} -> {row['source_url']}")
    (MANIFEST_DIR / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print(json.dumps({"records": len(rows), "counts": counts, "warnings": len(warnings)}, default=dict))


if __name__ == "__main__":
    main()
