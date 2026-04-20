# Oversight Semantic Search

A reusable semantic-search engine for exploring historical **Office of Inspector General (OIG)** oversight reports using natural language queries or draft project proposals.

This package builds a cached latent semantic index from a scraped SQLite database of oversight reports and supports:

* free-text search
* proposal similarity lookup
* CLI workflows
* Streamlit UI exploration
* integration with external applications (e.g., Project Proposal App)

---

## Features

### Semantic Report Search

Search oversight reports using natural language:

```text
contract oversight for other transactions
```

Returns ranked matches with similarity scores and metadata.

---

### Proposal Similarity Matching

Compare a draft project proposal against historical oversight work:

```python
search_project(title, objective, top_k=10)
```

Outputs the most similar prior OIG reports.

---

### Cached Vector Index

* Automatically builds a latent semantic index
* Stored locally for fast reuse
* Supports automatic rebuild fallback if cache is corrupted
* Uses safe temp-file writes during indexing

---

### Multiple Interfaces

Use whichever workflow fits your needs:

| Interface    | Use Case                             |
| ------------ | ------------------------------------ |
| CLI          | scripting + automation               |
| Python API   | integration into analytics pipelines |
| Streamlit UI | interactive exploration              |

---

## Repository Structure

```text
OversightSemanticSearch/
│
├── app.py
├── pyproject.toml
├── src/
│   └── oversight_semantic_search/
│       ├── cli.py
│       ├── config.py
│       └── index.py
│
└── README.md
```

---

## Installation

From the repository root:

```bash
pip install -e .
```

This installs the package in editable mode and enables:

```bash
oversight-search
```

CLI usage.

---

## Data Requirements

The index is built from a local SQLite database containing scraped OIG report metadata and summaries.

Configure the database path in:

```text
src/oversight_semantic_search/config.py
```

before building the index.

---

## Building the Semantic Index

Run:

```bash
oversight-search build --rebuild
```

This creates a cached semantic index for fast retrieval.

The index only needs rebuilding when:

* the database changes
* the embedding model changes
* the cache becomes unreadable

---

## CLI Usage

### Free-Text Search

```bash
oversight-search query "contract oversight for other transactions"
```

Returns ranked report matches.

---

### Proposal Similarity Search

```bash
oversight-search project \
  --title "Depot maintenance readiness risks" \
  --objective "Assess sustainment risks affecting aircraft engine availability"
```

Returns the most similar historical reports.

---

## Python API Usage

Import directly into your own applications:

```python
from oversight_semantic_search.index import search_project

results = search_project(
    title="Depot maintenance readiness risks",
    objective="Assess sustainment risks affecting aircraft engine availability",
    top_k=10,
)

for r in results:
    print(r["title"], r["score"])
```

This interface powers the **Project Proposal App** integration.

---

## Running the Streamlit Interface

Launch the interactive search UI:

```bash
python -m streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

The UI supports exploratory search across oversight reports using natural-language queries.

---

## Integration Example

This package is designed to support downstream tools such as:

```text
ProjectProposalApp
```

where it provides:

* similar-report lookup
* precedent discovery
* audit portfolio context

Example workflow:

1. Classify proposal into TMPC category
2. Retrieve similar historical reports
3. Review summaries and links
4. refine proposal scope

---

## Configuration

Edit:

```text
src/oversight_semantic_search/config.py
```

to customize:

* database location
* embedding model
* cache directory
* index filename

---

## Typical Workflow

Build index once:

```bash
oversight-search build --rebuild
```

Search reports:

```bash
oversight-search query "other transaction authority oversight"
```

Compare a proposal:

```bash
oversight-search project --title "..." --objective "..."
```

Launch UI:

```bash
python -m streamlit run app.py
```

---

## Future Improvements

Planned enhancements include:

* hybrid keyword + embedding search
* agency filtering
* date-range filtering
* exportable search results
* batch proposal similarity mode
* FAISS index support for larger corpora

---

## Author

Created by **Rachel Jakielski**

Designed to support oversight analytics, audit planning, and cross-OIG precedent discovery workflows.
