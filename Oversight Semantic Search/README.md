# Oversight Semantic Search

Semantic search over the report corpus collected by the sibling `OIG Scrape` project.

The application supports:

- standalone querying through a CLI or Streamlit UI
- project-to-report similarity search for a title plus objective
- a reusable Python API that other apps can import

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

## Build the index

The default configuration reads the SQLite database produced by:

- `C:\Users\Owner\Projects\OIG Scrape\data\oig_reports.sqlite3`

Build the index with:

```powershell
oversight-search build
```

You can override defaults with environment variables:

- `OSS_OIG_DB_PATH`
- `OSS_INDEX_DIR`
- `OSS_CHUNK_CHAR_LIMIT`
- `OSS_MAX_FEATURES`
- `OSS_LATENT_DIMENSIONS`

## Standalone query

CLI:

```powershell
oversight-search query "contract oversight for other transactions"
```

Project similarity:

```powershell
oversight-search project --title "Audit of depot maintenance readiness" --objective "Assess whether controls over aircraft engine repairs support readiness and accountability."
```

Streamlit UI:

```powershell
streamlit run app.py
```

## Reuse from another app

```python
from oversight_semantic_search.index import SemanticSearchIndex

index = SemanticSearchIndex()
results = index.search_project(
    title="Audit of depot maintenance readiness",
    objective="Assess whether controls over aircraft engine repairs support readiness and accountability.",
    top_k=10,
)
```

Each result includes the report title, summary, publication date, agency metadata, source URLs, and a similarity score.
