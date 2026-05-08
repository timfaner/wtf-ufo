# Quality Gates

Before claiming the pipeline is complete, verify actual artifacts.

## Manifest

- `data/manifest/records.jsonl` exists.
- `data/manifest/pdf_records.jsonl` exists.
- Counts in `data/manifest/summary.md` match parsed rows.

## Extraction

- `data/extracted/documents.jsonl` exists.
- `data/extracted/pages.jsonl` exists.
- `data/extracted/images.jsonl` exists.
- Every downloaded PDF record has an extraction row.

## OCR and Final Text

- `data/extracted/ocr/ocr_pages.jsonl` exists after OCR.
- `data/extracted/final_text/pages.jsonl` exists after merge.
- Low/no embedded-text pages with images should have OCR where possible.

## Curated Text

- `data/curated/readable/documents.jsonl` exists.
- `data/curated/readable/pages.jsonl` exists.
- `data/curated/search/chunks.jsonl` exists.
- `data/curated/search/chunks_default.jsonl` exists.
- `data/curated/search/chunks_excluded.jsonl` exists.
- `data/curated/llm_ready/chunks.jsonl` exists.
- Default chunks must include `chunk_id`, `record_id`, `page`, `text`, `quality`, `readable_page_path`, and `verbatim_page_path`.

## Graph

- `data/graph/knowledge_graph.json` exists.
- `data/graph/events.md` exists.
- `data/graph/knowledge_graph_view.html` exists if the viewer was requested.
- PDF record nodes include `readable_doc_path` after curation.

## Publishing

- `.gitignore` excludes heavy rebuildable data.
- `git status --short` does not show raw PDFs, extracted images, OCR pages, final text documents, or full curated text corpora.

