# ⚖️ Legal Parser: Intelligent Medical Record Pre-Processor

**Legal Parser** is a powerful Python-based tool designed to intelligently process large, unstructured medical and legal documents, transforming them from chaotic PDFs into clean, queryable, and AI-ready structured data.

It automates the tedious process of extracting, segmenting, and enriching information from documents like medical records, preparing them for downstream tasks such as summarization, timeline generation, and data analysis.

[![Python CI](https://github.com/defatpm/legal_parser/actions/workflows/ci.yml/badge.svg)](https://github.com/defatpm/legal_parser/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/defatpm/legal_parser/branch/main/graph/badge.svg?token=YOUR_CODECOV_TOKEN)](https://codecov.io/gh/defatpm/legal_parser)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ Features

Legal Parser offers a multi-faceted interface to streamline your document processing workflow:

- **Automated OCR**: Extracts text from scanned PDFs using Tesseract.
- **Intelligent Segmentation**: Divides documents into meaningful sections (e.g., "Patient History," "Diagnosis") using heuristics and NLP.
- **Metadata Enrichment**: Enriches segments with critical metadata like dates, providers, and document types using spaCy.
- **Structured Output**: Generates clean, structured JSON output, ready for AI models or database ingestion.
- **Interactive Web Interface**: A user-friendly Streamlit app for single & batch processing, real-time progress tracking, and results visualization.
- **Command-Line Interface**: For scripting and programmatic processing.
- **Batch Processing**: Process multiple documents at once with concurrent workers.
- **Flexible Export**: Download results in JSON, CSV, or as a ZIP archive.

---

## 🏛️ Architecture

The processing pipeline is designed for modularity and scalability:

```
PDF ─► OCR Engine ─► Segmenter ─► Metadata Enricher ─► Timeline Builder ─► JSON / DB
                                        │                               │
                                        └───────────► Metrics & Logs ◄──┘
```

1.  **Ingestion & OCR**: Validates and extracts text from PDFs, using OCR if necessary.
2.  **Segmentation**: Splits raw text into logical blocks based on document structure and content.
3.  **Enrichment**: Parses segments to extract entities, dates, and other key metadata.
4.  **Timeline Builder**: Organizes extracted events chronologically.
5.  **Output**: Delivers structured data through a CLI, Web Interface, or a planned REST API.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- [Tesseract OCR Engine](https://tesseract-ocr.github.io/tessdoc/Installation.html) installed and available in your system's PATH.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/defatpm/legal_parser.git
    cd legal_parser
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 💻 Usage

You can interact with Legal Parser in two primary ways:

### 1. Interactive Web Interface

The most user-friendly way to use the tool. It provides a complete GUI for all features.

**To run the web interface:**

```bash
streamlit run src/web_interface.py
```

Navigate to `http://localhost:8501` in your browser to access the dashboard for uploading files, monitoring progress, and viewing results.

### 2. Command-Line Interface (CLI)

Ideal for scripting and integration into automated workflows.

**To process a single PDF:**

```bash
python src/process_pdf.py --input path/to/your/document.pdf --output path/to/output.json
```

---

## ✅ Testing

To ensure reliability, the project includes a suite of tests.

**To run the tests:**

```bash
pytest
```

**To run tests with coverage:**
```bash
pytest --cov=src
```

---

## 🤝 Contributing

Contributions are welcome! Whether it's bug reports, feature requests, or code contributions, please feel free to open an issue or submit a pull request.

Check out the `CONTRIBUTING.md` for more details on how to get started.

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.