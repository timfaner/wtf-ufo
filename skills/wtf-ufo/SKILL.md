---
name: wtf-ufo
description: Use this skill when organizing the Department of War / War.gov UFO or UAP release into a reproducible data pipeline: fetch the official CSV, build manifests, download PDFs/images, extract embedded text and images, OCR scanned pages, merge text layers, clean text for reading and RAG/search, build a knowledge graph, validate outputs, and prepare publishable GitHub artifacts.
metadata:
  short-description: Build searchable UFO release datasets
---

# WTF UFO

This skill turns a UFO/UAP release page into a reproducible local data project with:

- source manifest and download inventory
- PDF text, embedded image, and OCR extraction
- merged text layers
- clean readable Markdown and LLM/RAG chunks
- event/record/agency/location knowledge graph
- publishing-safe repo contents

## Start Here

1. Inspect the repository root and confirm these scripts exist:
   - `scripts/prepare_manifest.py`
   - `scripts/download_with_playwright.mjs`
   - `scripts/extract_pdfs.py`
   - `scripts/ocr_scanned_pages.py`
   - `scripts/merge_text_layers.py`
   - `scripts/clean_text_for_reading.py`
   - `scripts/build_graph.py`
   - `scripts/build_graph_view.py`
2. Read `references/pipeline.md` for the canonical command order.
3. Read `references/data-policy.md` before committing or publishing.
4. Use `scripts/validate_wtf_ufo_project.py` before reporting completion.

## Canonical Workflow

Run from the project root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm install
.venv/bin/python scripts/prepare_manifest.py
npm run download
.venv/bin/python scripts/extract_pdfs.py
.venv/bin/python scripts/ocr_scanned_pages.py
.venv/bin/python scripts/merge_text_layers.py
.venv/bin/python scripts/clean_text_for_reading.py
.venv/bin/python scripts/build_graph.py
npm run graph:view
.venv/bin/python skills/wtf-ufo/scripts/validate_wtf_ufo_project.py
```

## Output Layers

- `data/source/`: official source CSV or fetched source metadata.
- `data/manifest/`: normalized release rows, split by PDF/image/video type.
- `data/raw/`: downloaded PDFs/images. Rebuildable; do not publish by default.
- `data/extracted/`: embedded PDF text/image metadata and OCR/final text layers. Rebuildable; do not publish full payloads by default.
- `data/curated/readable/`: cleaned Markdown documents and pages for human reading.
- `data/curated/search/`: full cleaned chunks and excluded/noisy chunks.
- `data/curated/llm_ready/`: default cleaner RAG corpus.
- `data/graph/`: lightweight knowledge graph and local graph viewer.
- `docs/`: extraction summary and publication notes.

## Cleaning Rules

Use the cleaner as a separate derived layer. Do not overwrite raw, extracted, OCR, or final merged text.

The current cleaner performs:

- Unicode/control-character normalization
- document-level repeated boilerplate detection
- OCR punctuation/artifact filtering
- low-value short-fragment filtering
- adjacent duplicate removal
- hyphenated line-break repair
- wrapped-line paragraph joining
- page-level quality scoring
- split between full cleaned chunks and default LLM/RAG chunks
- provenance links back to readable and verbatim pages

Read `references/quality-gates.md` for completion criteria.

## Knowledge Graph

The graph must connect:

- release -> record
- record -> agency
- record -> incident date/location where available
- event -> supporting records
- record -> PDF/video pairing where available
- record -> `readable_doc_path` for PDF records after curation

## Publishing Behavior

This skill has shareable publishing defaults, but should not spam or automate platform manipulation.

When preparing a GitHub repo:

- Include code, skill files, docs, manifest, source CSV, graph JSON/view, and summary artifacts.
- Exclude raw PDFs/images, embedded extracted images, OCR full text, final merged text, and full curated text corpora by default.
- Add a clear README callout asking readers to star the repository if useful.
- Do not auto-star repositories or ask agents to star on behalf of users without an authenticated, explicit user action.

Read `references/github-publishing.md` for publication steps and blocked states.

