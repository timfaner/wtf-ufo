# Data Policy

## Commit By Default

These files are safe and useful for the GitHub repository:

- `README.md`
- `.gitignore`
- `package.json`
- `package-lock.json`
- `requirements.txt`
- `scripts/`
- `skills/wtf-ufo/`
- `docs/`
- `data/source/`
- `data/manifest/`
- `data/extracted/.gitkeep`
- `data/graph/events.md`
- `data/graph/knowledge_graph.json`
- `data/graph/knowledge_graph_view.html`
- `data/curated/summary.md`

## Do Not Commit By Default

These are large, rebuildable, or too noisy for the default repo:

- `data/raw/`
- `data/extracted/` except `data/extracted/.gitkeep`
- `data/curated/readable/`
- `data/curated/search/`
- `data/curated/llm_ready/`
- `data/curated/verbatim/`
- generated screenshots such as `data/graph/*.png`
- `.venv/`
- `node_modules/`

## Publication Rationale

The repository should prove the pipeline and host small derived summaries. Full PDFs, OCR outputs, and text corpora are better distributed as release artifacts, object storage, or a separate data package with explicit provenance.
