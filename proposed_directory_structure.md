# Proposed Directory Structure (Optimized)

This revised structure builds upon the existing project layout, aiming for better organization, clarity, and scalability. It refines the original proposal by retaining the modularity of the current system while improving naming and separation of concerns.

```
legal_parser/
├── pyproject.toml           # Project metadata, dependencies (Poetry/Hatch), and tool config
├── requirements.txt         # For pip-based environments, can be generated
├── config.yaml              # Centralized application configuration
├── data/                    # Sample input and output data, not part of the package
│   ├── sample/
│   └── output/
├── docs/                    # Project documentation
├── scripts/                 # Standalone helper scripts (e.g., data generation)
├── src/
│   ├── legal_parser/        # Main installable package
│   │   ├── __init__.py
│   │   ├── main.py          # Main CLI entry point
│   │   ├── api/             # FastAPI application module
│   │   │   ├── __init__.py
│   │   │   ├── main.py      # FastAPI app, routes
│   │   │   └── models.py    # API-specific data models (Pydantic)
│   │   ├── core/            # Core data models used across the application
│   │   │   ├── __init__.py
│   │   │   └── document.py
│   │   ├── processing/      # Core document processing logic
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py  # Orchestrates the processing steps
│   │   │   ├── text_extractor.py
│   │   │   ├── segmenter.py
│   │   │   └── timeline_builder.py
│   │   ├── utils/           # Shared, low-level utilities
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── error_handler.py
│   │   └── web/             # Web UI module
│   │       ├── __init__.py
│   │       └── app.py       # The Streamlit/Flask application
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── integration/
│   └── unit/
└── README.md
```

### Key Changes & Rationale:

1.  **`src/legal_parser/` Layout:** Introduces a nested `legal_parser` directory. This is a standard Python packaging practice (`src-layout`) that clearly separates the source code that will be installed as a package from other project files (like `tests`, `scripts`, `docs`).
2.  **Clear Entry Points:**
    *   `src/legal_parser/main.py`: A single, clear entry point for the command-line interface.
    *   `src/legal_parser/api/main.py`: The entry point for the API service.
    *   `src/legal_parser/web/app.py`: The entry point for the web interface.
    *   This model removes the need for multiple `run_*.py` scripts in the project root.
3.  **Renamed for Clarity:**
    *   `processors/` -> `processing/`: More accurately describes the domain of this module.
    *   `models/` -> `core/`: Renamed to distinguish the core application data models (like `Document`) from the API-specific models (`api/models.py`).
4.  **Modular & Scalable:** Retains the modularity of the original codebase (e.g., separate files for `text_extractor`, `segmenter`), which was a good feature. This structure is easy to extend.
5.  **Top-Level Organization:** Moves non-package files like `scripts/` and `docs/` to the root for better organization. `config.yaml` also stays at the root for easy access.
