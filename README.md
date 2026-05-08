# WTF UFO

Reproducible UFO/UAP archive extraction for the Department of War / War.gov public release.

This repository turns the official UFO release at `https://www.war.gov/UFO/` into a structured, searchable research workspace: manifests, PDF download inventory, OCR, cleaned text, RAG-ready chunks, and a lightweight knowledge graph of records, events, agencies, dates, locations, and pairings.

If this project saves you time, please star and follow the repo so more UFO/UAP researchers, archivists, and data builders can find it.

## What This Is

The War.gov release includes scanned historical PDFs, images, metadata rows, and linked video records. A lot of the useful information is buried in difficult-to-search documents.

`wtf-ufo` provides a repeatable pipeline to:

- normalize the official release CSV into machine-readable manifests
- download the official PDFs/images through a browser-backed downloader
- extract embedded PDF text and embedded images
- run OCR on scanned pages using local macOS Vision
- merge embedded text and OCR into final page/document text
- clean scattered OCR output into readable Markdown
- build full and default RAG/search chunk indexes
- generate a knowledge graph across records, events, agencies, dates, locations, and pairings
- package the workflow as a reusable Codex skill

## Repository Contents

- `data/source/uap-csv.csv`: official source CSV.
- `data/manifest/`: normalized release manifests split by record type.
- `data/graph/knowledge_graph.json`: graph of release, records, events, agencies, locations, dates, and pairings.
- `data/graph/knowledge_graph_view.html`: self-contained local graph viewer.
- `data/curated/summary.md`: summary of the cleaned text layer generated locally.
- `scripts/`: reproducible extraction, OCR, cleaning, graph, and viewer scripts.
- `skills/wtf-ufo/`: reusable Codex skill for running and validating the workflow.
- `docs/extraction-summary.md`: current extraction counts and caveats.
- `docs/publishing.md`: what is included/excluded from the public repo.
- `deploy/wtf-ufo/`: lightweight static deploy artifact for the graph view.

Large rebuildable artifacts are intentionally not committed by default: raw PDFs, extracted images, OCR text, final merged text, and full cleaned corpora.

## Quick Start

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

The official site may block plain `curl` PDF downloads. `npm run download` uses Playwright/Chrome and page-session fetches to download the official files.

## Outputs

After running the full pipeline locally, the main generated layers are:

- `data/raw/`: downloaded PDFs/images.
- `data/extracted/`: PDF text, page metadata, embedded image metadata, OCR, and final merged text.
- `data/curated/readable/`: cleaned Markdown documents and pages for direct reading.
- `data/curated/search/chunks.jsonl`: full cleaned search corpus.
- `data/curated/search/chunks_default.jsonl`: cleaner default RAG corpus.
- `data/curated/search/chunks_excluded.jsonl`: noisy/low-confidence chunks retained for audit.
- `data/curated/llm_ready/chunks.jsonl`: default LLM/RAG input.
- `data/curated/verbatim/pages/`: normalized verbatim evidence layer.
- `data/graph/knowledge_graph.json`: graph data.
- `data/graph/knowledge_graph_view.html`: local interactive graph view.

## Graph Viewer

Generate the self-contained graph page:

```bash
npm run graph:view
```

Then open:

```text
data/graph/knowledge_graph_view.html
```

The page embeds `data/graph/knowledge_graph.json`, so it works from the local file system without a dev server.

## The `wtf-ufo` Skill

This repo includes a reusable Codex skill at:

```text
skills/wtf-ufo/
```

Use it when you want an agent to run, repair, validate, or publish the full UFO extraction workflow.

The skill is organized as:

```text
skills/wtf-ufo/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── data-policy.md
│   ├── github-publishing.md
│   ├── pipeline.md
│   └── quality-gates.md
└── scripts/
    └── validate_wtf_ufo_project.py
```

To install it locally for Codex-style skill discovery:

```bash
mkdir -p ~/.codex/skills/wtf-ufo
cp -R skills/wtf-ufo/. ~/.codex/skills/wtf-ufo/
```

Then ask an agent to use `wtf-ufo` for this repository. The skill will route the agent through the pipeline, data policy, quality gates, and publishing rules.

## Validation

Run the built-in project validator:

```bash
.venv/bin/python skills/wtf-ufo/scripts/validate_wtf_ufo_project.py
```

Expected result:

```json
{
  "status": "ok",
  "failures": [],
  "warnings": []
}
```

The validator checks the publishable project layout, manifest counts, graph linkage, and ignore policy for large rebuildable data.

## Current Snapshot

The local extraction run produced:

- 161 official release records
- 119 PDF records
- 4,182 PDF pages processed
- 4,258 embedded images indexed
- 3,605 OCR page rows
- 5,241 full cleaned search chunks
- 4,012 default LLM/RAG chunks
- 388 graph nodes
- 736 graph edges
- 99 event nodes

See `docs/extraction-summary.md` for details.

## Data Policy

The public GitHub repo is intentionally a reproducible workflow and lightweight index package, not a multi-gigabyte data dump.

Committed by default:

- source CSV
- manifests
- extraction/curation summaries
- knowledge graph JSON/viewer
- scripts
- `wtf-ufo` skill
- docs

Excluded by default:

- raw PDFs/images
- extracted embedded images
- OCR text payloads
- final merged text corpus
- full cleaned Markdown/corpus output
- local virtualenv and Node dependencies

If you need the full corpus, run the pipeline locally from the official release source.

## Follow Along

If you care about UFO/UAP records, public archives, OCR, RAG datasets, or knowledge graphs, star and follow this repo:

```text
https://github.com/timfaner/wtf-ufo
```

It helps other researchers discover the workflow and makes it easier to coordinate improvements.

## Caveat

OCR is machine-generated from historical scans. It is useful for search, clustering, RAG, and graph construction, but direct quotations should be checked against the original PDF page.
