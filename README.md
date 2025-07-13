# ⚖️ Legal Parser: Intelligent Document Pre-Processor

**Legal Parser** is a powerful tool that reads complex legal and medical documents, like a stack of messy papers, and neatly organizes them into a structured, easy-to-understand digital format. It's like having a super-smart assistant that can instantly sort, label, and create a timeline of events from a dense file, making it ready for analysis by lawyers, doctors, or AI.

[![Python CI](https://github.com/defatpm/legal_parser/actions/workflows/ci.yml/badge.svg)](https://github.com/defatpm/legal_parser/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/Coverage-80%2B%25-brightgreen.svg)](./htmlcov/index.html)

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
-   **REST API**: FastAPI-based backend for programmatic access and integration.
-   **Docker Support**: Containerized deployment with Docker Compose for easy setup.
-   **Batch Processing**: Handle multiple documents simultaneously with progress tracking.
-   **High Test Coverage**: 80%+ test coverage ensuring reliability and maintainability.

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
-   [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (recommended)
-   [Tesseract OCR Engine](https://tesseract-ocr.github.io/tessdoc/Installation.html) (optional, for scanned documents)

### Quick Start with Docker (Recommended)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/defatpm/legal_parser.git
    cd legal_parser
    ```

2.  **Start the services:**
    ```bash
    docker-compose up --build
    ```

3.  **Access the application:**
    - **Web Interface**: http://localhost:8502
    - **API Documentation**: http://localhost:8000/docs
    - **API Health Check**: http://localhost:8000/health/readiness

### Manual Installation

If you prefer to run without Docker:

1.  **Clone and install dependencies:**
    ```bash
    git clone https://github.com/defatpm/legal_parser.git
    cd legal_parser
    pip install -r requirements.txt
    ```

2.  **Download the spaCy model:**
    ```bash
    python -m spacy download en_core_web_sm
    ```

3.  **Run the applications:**
    ```bash
    # Start the API server
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
    
    # Start the web interface (in another terminal)
    streamlit run src/interfaces/web/app.py --server.port 8501
    ```

---

## 💻 Usage

You can interact with Legal Parser in multiple ways:

### 1. Interactive Web Interface

The most user-friendly way to use the tool. It supports single and batch document processing with real-time progress tracking and results visualization.

**Features:**
- Upload single or multiple PDF files
- Real-time processing progress
- Interactive timeline visualization
- Processing history and results management
- Settings configuration

Access via: http://localhost:8502 (when using Docker) or http://localhost:8501 (manual setup)

### 2. REST API

Programmatic access for integration into other applications.

**Key endpoints:**
- `POST /api/process` - Process a single document
- `POST /api/batch` - Process multiple documents
- `GET /api/status/{task_id}` - Check processing status
- `GET /health/readiness` - Health check

API documentation available at: http://localhost:8000/docs

### 3. Command-Line Interface (CLI)

Ideal for scripting and integration into automated workflows.

**To process a single PDF:**
```bash
python src/process_pdf.py --input path/to/your/document.pdf --output path/to/output.json
```

**For batch processing:**
```bash
python src/batch_processor.py --input-dir path/to/pdfs/ --output-dir path/to/results/
```

---


## 🧪 Development & Testing

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests

# Generate coverage report
pytest --cov=src --cov-report=html --cov-fail-under=80
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check --fix .

# Type checking
mypy src/
```

## 📁 Project Structure

```
src/
├── api/                    # FastAPI backend
│   ├── main.py            # API entry point
│   ├── models.py          # Pydantic models
│   └── tasks.py           # Background tasks
├── interfaces/web/         # Streamlit web interface
│   ├── app.py             # Main web app
│   ├── pages/             # Individual pages
│   └── components/        # Reusable components
├── processors/            # Core processing logic
│   ├── pdf_extractor.py   # PDF text extraction
│   ├── document_segmenter.py # Document segmentation
│   └── timeline_builder.py   # Timeline generation
├── models/               # Data models
├── utils/               # Shared utilities
└── ...
```

## 🗺️ Roadmap

Recent achievements:
- ✅ **Comprehensive Testing**: 80%+ test coverage achieved
- ✅ **CI/CD Automation**: GitHub Actions for automated testing and linting
- ✅ **Docker Support**: Full containerization with Docker Compose
- ✅ **REST API**: FastAPI backend with async processing

Future plans:
-   **Performance Optimization**: Implementing parallel processing for even faster batch jobs
-   **Enhanced NLP**: Advanced entity recognition and relationship extraction
-   **Multi-format Support**: Support for Word documents, images, and other formats
-   **Cloud Deployment**: Kubernetes deployment templates and cloud integration

---

## 🤝 Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
