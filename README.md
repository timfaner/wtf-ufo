# UFO Archive Extraction

This project organizes the Department of War PURSUE UFO/UAP Release 01 records from `https://www.war.gov/UFO/`.

If this pipeline saves you time, star the repo so other UFO/UAP researchers can find it.

Current local source of truth:

- `data/source/uap-csv.csv`: official release CSV fetched from the page.
- `data/manifest/`: normalized record manifests generated from the CSV.
- `data/raw/pdfs/`: downloaded PDF originals.
- `data/extracted/`: extracted PDF text, page metadata, and embedded images.
- `data/curated/readable/`: cleaned Markdown documents and pages for direct reading.
- `data/curated/search/`: JSONL page/chunk indexes for search and RAG.
- `data/curated/llm_ready/chunks.jsonl`: cleaner default LLM/RAG corpus with noisy OCR pages excluded but provenance retained.
- `data/graph/knowledge_graph.json`: graph of release, records, events, agencies, dates, locations, and pairings.
- `skills/wtf-ufo/`: reusable Codex skill that documents and validates the full pipeline.
- `docs/extraction-summary.md`: current extraction counts and caveats.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
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

The official site blocks plain `curl` PDF downloads with Akamai `403`. `npm run download` uses Playwright/Chrome and page-session fetches to download the official files.

## Visualize the graph

Generate the self-contained interactive graph view:

```bash
npm run graph:view
```

Then open `data/graph/knowledge_graph_view.html` in a browser. The page embeds `data/graph/knowledge_graph.json`, so it works from the local file system without a dev server.

## OCR

`scripts/ocr_scanned_pages.py` uses local macOS Vision OCR for pages with little or no embedded text. Outputs are written under `data/extracted/ocr/` and can be resumed.

## Curated Text

`scripts/clean_text_for_reading.py` creates a separate LLM/search-ready layer without changing the original extracted text. The cleaner applies document-level boilerplate detection, OCR/control-character normalization, punctuation-artifact removal, low-value OCR fragment filtering, hyphenated-line repair, wrapped-line paragraph joining, and page-level provenance.

Use `data/curated/search/chunks.jsonl` for the full cleaned corpus. Use `data/curated/search/chunks_default.jsonl` or `data/curated/llm_ready/chunks.jsonl` as the default RAG corpus when you want cleaner retrieval results.

## Skill

The repo includes a reusable skill at `skills/wtf-ufo/`. Use it when you want an agent to run, repair, validate, or publish the full UFO extraction workflow.

The skill keeps `SKILL.md` short and moves detailed rules into:

- `skills/wtf-ufo/references/pipeline.md`
- `skills/wtf-ufo/references/data-policy.md`
- `skills/wtf-ufo/references/quality-gates.md`
- `skills/wtf-ufo/references/github-publishing.md`

## Publishing

The default GitHub repo should include code, docs, the skill, source CSV, manifests, and lightweight graph artifacts. It should not include raw PDFs, extracted images, OCR text, final merged text, or full curated corpora by default. See `docs/publishing.md`.
