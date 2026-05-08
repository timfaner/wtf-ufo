# WTF UFO Pipeline

Run all commands from the project root.

## Inputs

The project expects the official release CSV at:

```text
data/source/uap-csv.csv
```

For the War.gov UFO release, the source page is:

```text
https://www.war.gov/UFO/
```

## Commands

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

## Notes

- `npm run download` uses Playwright because direct PDF downloads may be blocked by the official site.
- `ocr_scanned_pages.py` uses local macOS Vision OCR and can be resumed.
- `clean_text_for_reading.py` creates a derived layer; it must not mutate raw or OCR evidence.
- `build_graph.py` should be run after text cleaning so record nodes can link to readable documents.

