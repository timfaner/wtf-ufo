# Curated Text Summary

- Documents: 119
- Pages: 4182
- Search chunks: 5241
- Default LLM/RAG chunks: 4012
- Excluded/noisy chunks retained for audit: 1229
- Raw text characters: 5185553
- Clean text characters: 4997342

Cleaning method: document-level boilerplate detection, OCR/control-character normalization, punctuation-artifact removal, low-value OCR fragment filtering, hyphenated-line repair, wrapped-line paragraph joining, Markdown page structure, and retrieval chunks with page-level provenance.

`data/curated/search/chunks.jsonl` keeps every cleaned chunk. `data/curated/search/chunks_default.jsonl` and `data/curated/llm_ready/chunks.jsonl` are the cleaner default corpus for LLM/RAG use; they exclude empty pages, stamp-only pages, and pages flagged as likely OCR noise while retaining provenance back to readable and verbatim pages.

Original extracted text remains under `data/extracted/final_text/`. Normalized verbatim page text is also written under `data/curated/verbatim/pages/` so the cleaner LLM/search layer can be audited against the evidence layer.
