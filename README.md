# AIDB

AIDB is a lightweight local AI knowledge base for storing, searching, and exploring structured and unstructured knowledge without needing a full database service.

It is designed for:
- personal AI memory
- prototype retrieval systems
- document collections
- small-scale knowledge graphs
- experimentation with indexing and search

## Why AIDB?

Most AI tools are great at generating answers but weak at keeping long-lived memory. AIDB gives you a simple, inspectable place to store facts, snippets, notes, and documents with metadata and search.

## Features

- Store documents with title, content, tags, and metadata
- Search by keyword overlap and metadata match
- Persistent JSON storage
- Simple Python API
- Works in local notebooks, scripts, and prototypes
- No external services required

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m aidb --help
```

## Example

```python
from aidb import AIDB

store = AIDB("./demo.db.json")
store.add_document(
    title="AI Memory",
    content="AI memory systems store facts and context to support follow-up conversations.",
    tags=["ai", "memory", "retrieval"],
    metadata={"source": "notes", "category": "concept"},
)

results = store.search("memory ai context")
for record in results:
    print(record.title, record.score)
```

## Project layout

```text
AIDB/
├── README.md
├── pyproject.toml
├── .gitignore
├── aidb/
│   ├── __init__.py
│   ├── __main__.py
│   ├── core.py
│   └── store.py
├── data/
│   └── sample_documents.json
├── examples/
│   └── demo.py
├── tests/
│   └── test_basic.py
└── .venv/
```

## License

Apache 2.0
