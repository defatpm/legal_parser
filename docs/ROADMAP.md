# Project Roadmap

This document outlines the development roadmap and future plans for the Legal Parser project.

## Phase 1: Core Processing Engine (Completed)

-   **Project Scaffolding**: Set up `src-layout` structure, virtual environment, and modern Python tooling (`ruff`, `black`, `mypy`, `pre-commit`).
-   **Modular Processing Pipeline**: Refactored core logic into a `ProcessingPipeline` that orchestrates modular components (`TextExtractor`, `Segmenter`, etc.) using dependency injection.
-   **Core Components Implemented**:
    -   **PDF Extraction**: `PyMuPDF` with `Tesseract` OCR fallback.
    -   **Document Segmentation**: Regex-based boundary detection.
    -   **Metadata Extraction**: `spaCy` NLP and pattern matching for dates, providers, and document types.
    -   **Timeline Building**: Chronological sorting and intelligent chunking.
-   **Testing**: Comprehensive test suite with unit and integration tests, achieving over 70% code coverage.
-   **Web UI Decoupling**: Redesigned the Streamlit web interface to be a thin presentation layer, fully decoupled from the backend.

## Phase 2: Feature Expansion & Usability (In Progress)

-   **REST API Development**:
    -   Create a FastAPI-based web service with a `/process` endpoint.
    -   Add file upload handling and asynchronous processing.
    -   Implement request/response validation with Pydantic.
-   **Batch Processing**:
    -   Add directory-based batch processing via the CLI.
    -   Implement concurrent processing with configurable worker pools.
-   **Enhanced Output Formats**:
    -   Add CSV and Excel export options.
    -   Implement customizable output templates.

## Phase 3: Production & Operations (Future)

-   **Containerization**: Create an optimized Dockerfile and `docker-compose` setup for local development and production deployment.
-   **CI/CD Pipeline**: Enhance the existing GitHub Actions workflow with automated deployment, quality gates, and security scanning.
-   **Monitoring**: Add structured logging, metrics collection (e.g., Prometheus), and health checks.
-   **Security**: Implement secure file handling, temporary file cleanup, and audit logging.

## Phase 4: Advanced Features (Future)

-   Machine learning-based document classification and segmentation.
-   Advanced NLP for entity extraction and relationship mapping.
-   Integration with cloud storage (e.g., AWS S3, Google Cloud Storage).
-   Multi-language support.
