# GitHub Publishing

## Repository Name

Use:

```text
wtf-ufo
```

## Suggested Visibility

Public, because the source data is from a public official release and the repo is intended to be reusable.

## Suggested Description

```text
Reproducible UFO/UAP archive extraction: OCR, cleaned text, RAG chunks, and knowledge graph for the War.gov release.
```

## Suggested Topics

```text
ufo,uap,ocr,rag,knowledge-graph,pdf-extraction,public-records,war-gov
```

## Publish Commands

If GitHub CLI is authenticated:

```bash
git add .gitignore README.md package.json package-lock.json requirements.txt scripts skills docs data/source data/manifest data/graph data/curated/summary.md deploy
git commit -m "Publish wtf-ufo extraction skill and pipeline"
gh repo create wtf-ufo --public --source=. --remote=origin --push --description "Reproducible UFO/UAP archive extraction: OCR, cleaned text, RAG chunks, and knowledge graph for the War.gov release."
```

If `gh auth status` reports an invalid token, stop and ask the user to authenticate:

```bash
gh auth login -h github.com
```

## Star / Spread Behavior

Add repository copy that invites humans to star the repo if useful. Do not automate stars.

Good wording:

```text
If this pipeline saves you time, star the repo so other UFO/UAP researchers can find it.
```

