# WTF UFO

The UFO archive is public. It is not yet usable.

WTF UFO gives it a working memory.

It takes the War.gov UFO/UAP release, pulls down the official files, OCRs the scans, cleans the broken text, turns the documents into search chunks, and wires the whole thing into a knowledge graph of records, events, agencies, dates, locations, and supporting files.

Built for agents. Useful for researchers. Reproducible from the official source.

If this saves you time, star the repo and follow along:

```text
https://github.com/timfaner/wtf-ufo
```

## Why

The release is a pile of PDFs, scanned pages, images, metadata rows, and linked records.

That is not a research system. That is an archive waiting to be processed.

WTF UFO turns it into:

- a normalized manifest of every release record
- a browser-backed downloader for the official files
- embedded PDF text and image extraction
- OCR for scanned pages
- merged page/document text
- cleaned Markdown that humans can read
- RAG-ready chunks that agents can search
- a knowledge graph that connects events, records, agencies, dates, locations, PDFs, and media pairings
- a reusable Codex skill called `wtf-ufo`

The goal is simple: make the UFO files easier to read, search, connect, and build on.

## The Current Brain

The current local run produced:

- 161 release records
- 119 PDF records
- 4,182 PDF pages processed
- 4,258 embedded images indexed
- 3,605 OCR page rows
- 5,241 cleaned search chunks
- 4,012 default LLM/RAG chunks
- 388 graph nodes
- 736 graph edges
- 99 event nodes

The public repo keeps the workflow and lightweight indexes. It does not ship the multi-gigabyte raw/OCR corpus by default. Run the pipeline locally to rebuild it.

## Agent Install

WTF UFO is designed to be run by an agent.

Install the skill with `npx`:

```bash
npx --yes --package github:timfaner/wtf-ufo wtf-ufo
```

That copies the skill into:

```text
~/.codex/skills/wtf-ufo
```

Paste this into Codex or another coding agent inside the repo:

```text
Use the skill at skills/wtf-ufo.
Read SKILL.md first, then follow references/pipeline.md.
Run the full UFO extraction workflow and validate with skills/wtf-ufo/scripts/validate_wtf_ufo_project.py.
Do not commit raw PDFs, OCR text payloads, extracted images, or full cleaned corpora.
```

To install to a custom directory:

```bash
npx --yes --package github:timfaner/wtf-ufo wtf-ufo --target /path/to/skills/wtf-ufo
```

The skill includes:

- the command order
- the data policy
- quality gates
- GitHub publishing rules
- a validator for the publishable project layout

## Manual Run

If you want to run it yourself:

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

`npm run download` uses Playwright/Chrome because the official site may block plain command-line downloads.

## What You Get

After a full local run:

```text
data/raw/                         official PDFs and images
data/extracted/                   extracted PDF text, image metadata, OCR, final text
data/curated/readable/            cleaned Markdown for humans
data/curated/search/chunks.jsonl  full cleaned search corpus
data/curated/llm_ready/           cleaner default RAG corpus
data/curated/verbatim/            normalized evidence layer
data/graph/knowledge_graph.json   graph data
data/graph/knowledge_graph_view.html
```

Open the graph:

```bash
npm run graph:view
open data/graph/knowledge_graph_view.html
```

The graph viewer is self-contained and works from the local filesystem.

## The Skill

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

The important idea: the skill is the workflow.

An agent can read it, understand what to run, know what not to publish, validate the result, and keep the archive reproducible.

## Validation

```bash
.venv/bin/python skills/wtf-ufo/scripts/validate_wtf_ufo_project.py
```

Expected:

```json
{
  "status": "ok",
  "failures": [],
  "warnings": []
}
```

## What Is In GitHub

Included:

- source CSV
- normalized manifests
- graph JSON and local graph viewer
- summaries
- pipeline scripts
- the `wtf-ufo` skill
- docs

Excluded:

- raw PDFs and images
- extracted embedded images
- OCR text payloads
- final merged full text
- full cleaned Markdown/corpus output
- local dependency folders

This keeps the repo small and lets anyone rebuild the full archive from the public source.

## Source

Official release page:

```text
https://www.war.gov/UFO/
```

## Follow

This project is for people who want the UFO/UAP archive to be searchable, inspectable, and agent-ready.

Star the repo if you want more work like this:

```text
https://github.com/timfaner/wtf-ufo
```

## Caveat

OCR is machine-generated from historical scans. It is good for search, clustering, RAG, and graph construction. If you quote a record, check the original PDF page.
