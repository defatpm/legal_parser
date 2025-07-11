# ⚖️ Legal Parser: Intelligent Document Pre-Processor

**Legal Parser** is a powerful tool that reads complex legal and medical documents, like a stack of messy papers, and neatly organizes them into a structured, easy-to-understand digital format. It's like having a super-smart assistant that can instantly sort, label, and create a timeline of events from a dense file, making it ready for analysis by lawyers, doctors, or AI.

[![Python CI](https://github.com/defatpm/legal_parser/actions/workflows/ci.yml/badge.svg)](https://github.com/defatpm/legal_parser/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

### 🧸 Explain Like I'm 5 (ELI5)

Imagine you have a giant coloring book about a visit to the doctor. The pages are all mixed up! Some pages are about your temperature, some are notes the doctor wrote, and others are dates.

This tool is like a magic robot that:
1.  **Reads all the pages** for you, even the messy, scribbled ones.
2.  **Sorts the pages** into neat piles, like "Doctor's Notes," "Test Results," and "Important Dates."
3.  **Creates a simple list** of what happened and when, like "First, you felt sick," "Next, you saw the doctor," "Then, you got medicine."

So, instead of a jumbled mess, you get a clean, organized storybook of what happened.

---

## ✨ Features

-   **Automated Text Extraction**: Uses **PyMuPDF** for fast text extraction from PDFs, with **Tesseract OCR** as a fallback for scanned images.
-   **Intelligent Segmentation**: Divides documents into meaningful sections (e.g., "Patient History," "Diagnosis").
-   **Timeline Generation**: Automatically builds a chronological timeline of events from the document text.
-   **Structured Output**: Generates clean, structured JSON that is ready for AI models or databases.
-   **Interactive Web UI**: A user-friendly Streamlit app for easy document upload, processing, and visualization.
-   **Command-Line Interface**: For scripting, automation, and batch processing.

---

## 🏛️ Architecture Overview

The project follows a modern, modular `src-layout` structure. The core logic is orchestrated by a `ProcessingPipeline` that injects and manages a series of independent components. This design ensures a clear separation of concerns and makes the system highly testable and extensible.

```
Input (PDF) -> ProcessingPipeline
                  |
                  ├─> 1. TextExtractor (PyMuPDF/OCR)
                  ├─> 2. Segmenter
                  ├─> 3. TimelineBuilder
                  |
                  └─> Output (Document Object) -> (JSON, Web UI, API)
```

This decoupled architecture allows for flexible and independent development of the core logic, the web interface, and the API.

---

## 🚀 Getting Started

### Prerequisites

-   Python 3.9+
-   [Poetry](https://python-poetry.org/docs/#installation) for dependency management.
-   [Tesseract OCR Engine](https://tesseract-ocr.github.io/tessdoc/Installation.html) (optional, for scanned documents).

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/defatpm/legal_parser.git
    cd legal_parser
    ```

2.  **Install dependencies using Poetry:**
    This command creates a virtual environment and installs all necessary packages.
    ```bash
    poetry install
    ```

---

## 💻 Usage

You can interact with Legal Parser in two primary ways:

### 1. Interactive Web Interface

The most user-friendly way to use the tool.

**To run the web interface:**
```bash
poetry run streamlit run src/legal_parser/web/app.py
```
Navigate to `http://localhost:8501` in your browser to upload files and view results.

### 2. Command-Line Interface (CLI)

Ideal for scripting and integration into automated workflows.

**To process a single PDF:**
```bash
poetry run python src/legal_parser/main.py process-file --input-path path/to/your/document.pdf --output-path path/to/output.json
```

**To process a directory of PDFs:**
```bash
poetry run python src/legal_parser/main.py process-dir --input-path /path/to/docs --output-path /path/to/output_dir
```

---

## 🗺️ Roadmap

Our future plans include:

-   **Comprehensive Testing**: Building out a full suite of unit and integration tests.
-   **CI/CD Automation**: Setting up GitHub Actions for automated testing and linting.
-   **Performance Optimization**: Implementing parallel processing for even faster batch jobs.
-   **Enhanced Documentation**: Including more detailed API docs and usage examples.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
