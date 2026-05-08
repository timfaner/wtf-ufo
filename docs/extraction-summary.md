# Extraction Summary

Source: `https://www.war.gov/UFO/`

Snapshot fetched: May 8, 2026

## Manifest

- Records parsed from official CSV: 161
- PDF records: 119
- Unique downloaded PDF files: 116
- Standalone image records: 14
- Video records: 28
- Agencies: Department of State, Department of War, FBI, NASA

## Extracted PDF Content

- PDF records processed: 119
- PDF pages scanned by extractor: 4,182
- Embedded/extractable text characters: 917,400
- Embedded images extracted from PDFs: 4,258
- PDF records with no embedded text: 62
- PDF records with fewer than 100 embedded-text characters: 65

## OCR

- OCR engine: local macOS Vision (`scripts/vision_ocr.swift`)
- OCR page rows: 3,605
- OCR document rows: 74
- OCR text characters: 4,268,073
- Low-text pages with embedded images still missing OCR: 0

## Curated / LLM-Ready Text

- Curated documents: 119
- Curated pages: 4,182
- Full cleaned search chunks: 5,241
- Default LLM/RAG chunks: 4,012
- Excluded/noisy chunks retained for audit: 1,229
- Raw merged text characters: 5,185,553
- Cleaned text characters: 4,997,342

## Generated Outputs

- Normalized manifest: `data/manifest/records.jsonl`
- PDF text files: `data/extracted/text/`
- Per-document extraction index: `data/extracted/documents.jsonl`
- Per-page extraction index: `data/extracted/pages.jsonl`
- Extracted image index: `data/extracted/images.jsonl`
- OCR page index: `data/extracted/ocr/ocr_pages.jsonl`
- OCR text files: `data/extracted/ocr/pages/`
- Final merged text files: `data/extracted/final_text/`
- Clean readable Markdown: `data/curated/readable/`
- Clean search chunks: `data/curated/search/chunks.jsonl`
- Default LLM/RAG corpus: `data/curated/llm_ready/chunks.jsonl`
- Noisy-but-retained chunks: `data/curated/search/chunks_excluded.jsonl`
- Knowledge graph: `data/graph/knowledge_graph.json`
- Event index: `data/graph/events.md`

## Knowledge Graph

- Records represented: 161
- Nodes: 388
- Edges: 736
- Event nodes: 99

## Caveat

OCR is machine-generated from historical scans. It is suitable for search and network construction, but individual quotations should be checked against the original page image or PDF. The curated LLM/RAG layer intentionally filters likely OCR noise from the default corpus; full cleaned chunks and normalized verbatim pages are retained for audit.
