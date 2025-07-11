# Next Steps & Improvement Roadmap

This document outlines a strategic roadmap for enhancing the `legal_parser` project, building on the newly defined architecture. The suggestions are categorized for clarity and can be implemented incrementally.

---

### 1. Foundational Improvements (High Priority)

These tasks will improve project stability, maintainability, and developer experience.

-   **Dependency Management:**
    -   **Action:** Migrate from `requirements.txt` to **Poetry** or **Hatch** for robust dependency locking, environment management, and packaging.
    -   **Rationale:** This is a best practice for modern Python projects that simplifies setup and ensures reproducible builds.

-   **Comprehensive Testing:**
    -   **Action:** Develop a full test suite using `pytest`.
    -   **Scope:**
        -   **Unit Tests:** For individual components (`TextExtractor`, `Segmenter`, etc.) with mocked dependencies.
        -   **Integration Tests:** For the `ProcessingPipeline` to ensure components work together correctly.
        -   **API Tests:** To validate the FastAPI endpoints.
    -   **Rationale:** Guarantees reliability and prevents regressions.

-   **CI/CD Automation:**
    -   **Action:** Implement a GitHub Actions workflow (`.github/workflows/ci.yml`).
    -   **Workflow Steps:**
        1.  Install dependencies (using Poetry/Hatch).
        2.  Run the linter (`ruff`).
        3.  Execute the `pytest` suite.
    -   **Rationale:** Automates quality checks on every commit and pull request.

---

### 2. Performance & Optimization

These tasks focus on making the application faster and more efficient, especially for large documents.

-   **Efficient Text Extraction:**
    -   **Action:** Refactor `TextExtractor` to use **PyMuPDF (fitz)** as the primary extraction method. It's significantly faster for PDFs with embedded text.
    -   **Fallback:** Keep **Tesseract (OCR)** as a fallback for image-based or scanned PDFs.

-   **Parallel Batch Processing:**
    -   **Action:** Implement parallel processing for the CLI using Python's `concurrent.futures.ProcessPoolExecutor`.
    -   **Rationale:** Dramatically speeds up the processing of multiple documents by utilizing all available CPU cores.

-   **Memory Efficiency:**
    -   **Action:** Investigate and implement stream-based processing or chunking for very large documents to avoid loading the entire file into memory.

---

### 3. Documentation & Usability

These tasks will make the project easier for others to understand, use, and contribute to.

-   **Enhance README.md:**
    -   **Action:** Update the main `README.md` to include:
        -   Clear quick-start instructions (local setup and Docker).
        -   Code examples for the CLI.
        -   Screenshots of the web UI.
        -   An overview of the new project architecture.

-   **API Documentation:**
    -   **Action:** Leverage FastAPI's automatic OpenAPI/Swagger documentation generation.
    -   **Enhancement:** Add detailed descriptions and examples to Pydantic models and API endpoints for clarity.

-   **Centralized Logging:**
    -   **Action:** Implement a structured logging system (e.g., using the standard `logging` module) that can output to both the console and files.
    -   **Rationale:** Provides consistent and configurable logging across the CLI, API, and web components, replacing scattered `print` and `st.info` calls.
