# Publishing Plan

Repository name:

```text
wtf-ufo
```

Suggested description:

```text
Reproducible UFO/UAP archive extraction: OCR, cleaned text, RAG chunks, and knowledge graph for the War.gov release.
```

## Include

- `.gitignore`
- `README.md`
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
- `deploy/wtf-ufo/`

## Exclude By Default

- `data/raw/`
- `data/extracted/` except `data/extracted/.gitkeep`
- `data/curated/readable/`
- `data/curated/search/`
- `data/curated/llm_ready/`
- `data/curated/verbatim/`
- generated graph screenshots
- `.venv/`
- `node_modules/`

## Why

The GitHub repository should be a reproducible workflow and skill package, not a 5GB data dump. The large files are official source PDFs, extracted images, OCR text, and generated corpora that can be rebuilt from the official release.

If the full text corpus needs to be distributed later, publish it as a GitHub Release artifact, object-storage dataset, or separate data package with clear provenance.

## Publish Command

After GitHub CLI authentication:

```bash
git add .gitignore README.md package.json package-lock.json requirements.txt scripts skills docs data/source data/manifest data/graph data/curated/summary.md deploy
git commit -m "Publish wtf-ufo extraction skill and pipeline"
gh repo create wtf-ufo --public --source=. --remote=origin --push --description "Reproducible UFO/UAP archive extraction: OCR, cleaned text, RAG chunks, and knowledge graph for the War.gov release."
```
