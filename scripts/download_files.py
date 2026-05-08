#!/usr/bin/env python3
"""Download official PURSUE files with browser-like request headers."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifest/records.jsonl"
PDF_DIR = ROOT / "data/raw/pdfs"
IMAGE_DIR = ROOT / "data/raw/images"
THUMB_DIR = ROOT / "data/raw/thumbnails"
RESULTS = ROOT / "data/manifest/download-results.jsonl"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.war.gov/UFO/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def download(url: str, out_path: Path, retries: int = 3) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and out_path.stat().st_size > 0:
        return {"url": url, "path": str(out_path.relative_to(ROOT)), "status": "exists", "bytes": out_path.stat().st_size}

    for attempt in range(1, retries + 1):
        try:
            request = Request(quote_url(url), headers=HEADERS)
            with urlopen(request, timeout=120) as response:
                body = response.read()
                out_path.write_bytes(body)
                return {
                    "url": url,
                    "path": str(out_path.relative_to(ROOT)),
                    "status": "downloaded",
                    "http_status": response.status,
                    "bytes": len(body),
                }
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == retries:
                return {
                    "url": url,
                    "path": str(out_path.relative_to(ROOT)),
                    "status": "failed",
                    "error": repr(exc),
                }
            time.sleep(1.5 * attempt)
    return {"url": url, "path": str(out_path.relative_to(ROOT)), "status": "failed", "error": "unknown"}


def quote_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/%:@"), parts.query, parts.fragment))


def output_path(record: dict) -> Path | None:
    filename = record.get("filename")
    kind = record.get("kind")
    if not filename or kind not in {"PDF", "IMG"}:
        return None
    if kind == "PDF":
        return PDF_DIR / filename
    return IMAGE_DIR / filename


def main() -> None:
    records = read_jsonl(MANIFEST)
    results: list[dict] = []
    for record in records:
        source_url = record.get("source_url")
        out_path = output_path(record)
        if source_url and out_path:
            result = download(source_url, out_path)
            result.update({"record_id": record["id"], "kind": record["kind"], "title": record["title"]})
            print(f"{result['status']:10s} {record['kind']:3s} {out_path.name}")
            results.append(result)

        thumb_url = record.get("thumbnail_url")
        thumb_name = Path(thumb_url).name if thumb_url else ""
        if thumb_url and thumb_name:
            result = download(thumb_url, THUMB_DIR / thumb_name)
            result.update({"record_id": record["id"], "kind": "THUMB", "title": record["title"]})
            results.append(result)

    with RESULTS.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")

    summary: dict[str, int] = {}
    for result in results:
        summary[result["status"]] = summary.get(result["status"], 0) + 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
