#!/usr/bin/env python3
"""Validate the publishable WTF UFO project layout and key derived artifacts."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


REQUIRED_PATHS = [
    "README.md",
    ".gitignore",
    "requirements.txt",
    "package.json",
    "scripts/prepare_manifest.py",
    "scripts/download_with_playwright.mjs",
    "scripts/extract_pdfs.py",
    "scripts/ocr_scanned_pages.py",
    "scripts/merge_text_layers.py",
    "scripts/clean_text_for_reading.py",
    "scripts/build_graph.py",
    "scripts/build_graph_view.py",
    "skills/wtf-ufo/SKILL.md",
    "skills/wtf-ufo/references/pipeline.md",
    "skills/wtf-ufo/references/data-policy.md",
    "skills/wtf-ufo/references/quality-gates.md",
    "skills/wtf-ufo/references/github-publishing.md",
    "data/source/uap-csv.csv",
    "data/manifest/records.jsonl",
    "data/manifest/pdf_records.jsonl",
    "data/manifest/summary.md",
    "data/graph/knowledge_graph.json",
    "data/graph/events.md",
    "data/curated/summary.md",
]


PUBLISH_IGNORED_PREFIXES = [
    "data/raw/",
    "data/extracted/",
    "data/curated/readable/",
    "data/curated/search/",
    "data/curated/llm_ready/",
    "data/curated/verbatim/",
]


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def load_graph() -> dict:
    path = ROOT / "data/graph/knowledge_graph.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    failures: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED_PATHS:
        if not (ROOT / relative).exists():
            failures.append(f"missing required path: {relative}")

    manifest_records = count_jsonl(ROOT / "data/manifest/records.jsonl")
    pdf_records = count_jsonl(ROOT / "data/manifest/pdf_records.jsonl")
    if manifest_records < 1:
        failures.append("manifest records are empty")
    if pdf_records < 1:
        failures.append("PDF records are empty")

    graph = load_graph()
    if graph:
        metadata = graph.get("metadata", {})
        if metadata.get("record_count") != manifest_records:
            failures.append(
                f"graph record_count {metadata.get('record_count')} does not match manifest {manifest_records}"
            )
        record_nodes = [node for node in graph.get("nodes", []) if node.get("type") == "record"]
        pdf_nodes = [node for node in record_nodes if node.get("kind") == "PDF"]
        missing_readable = [node["id"] for node in pdf_nodes if not node.get("readable_doc_path")]
        if missing_readable:
            failures.append(f"PDF graph nodes missing readable_doc_path: {len(missing_readable)}")

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
    gitignore_lines = [line.strip() for line in gitignore.splitlines() if line.strip() and not line.startswith("#")]
    for prefix in PUBLISH_IGNORED_PREFIXES:
        pattern = prefix.rstrip("/")
        parent_wildcard = str(Path(prefix).parent / "*")
        child_wildcard = f"{pattern}/*"
        if (
            pattern not in gitignore_lines
            and prefix not in gitignore_lines
            and parent_wildcard not in gitignore_lines
            and child_wildcard not in gitignore_lines
        ):
            warnings.append(f"publish ignore pattern not found: {prefix}")

    result = {
        "status": "ok" if not failures else "failed",
        "manifest_records": manifest_records,
        "pdf_records": pdf_records,
        "failures": failures,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
