# Legal Parser: Intelligent Medical Record Pre-Processor

This is a Python-based tool designed to parse legal documents, with a focus on medical records, for use in AI models. It processes large PDFs by:
- Extracting content via OCR (for scanned documents).
- Segmenting text based on medical boundaries (e.g., sections like "Patient History" or "Diagnosis").
- Enriching segments with metadata (e.g., dates, providers, document types).
- Outputting structured JSON for downstream AI processing (e.g., summarization or timeline generation).

This project is in early development and serves as a prototype for handling unstructured medical/legal PDFs.

## Architecture
1. **Extraction**: Uses OCR to pull text from PDFs.
2. **Segmentation**: Identifies logical sections using heuristics (e.g., keywords, headings).
3. **Enrichment**: Adds metadata like extracted dates or entity recognition.
4. **Output**: Generates JSON with segments and metadata.

## Quick Start
1. Clone the repo: `git clone https://github.com/defatpm/legal_parser.git`
2. Create a virtual environment: `python -m venv venv` and activate it.
3. Install dependencies: `pip install -r requirements.txt`
4. Run the processor: `python src/process_pdf.py --input path/to/sample.pdf --output output.json`

Example:
- Input: A PDF medical record.
- Output: JSON like `[{"segment": "Patient History: ...", "metadata": {"date": "2025-07-10", "type": "history"}}]`

## Requirements
- Python 3.8+
- Tesseract OCR installed (for OCR functionality; see installation guide: https://tesseract-ocr.github.io/tessdoc/Installation.html)

## Examples
### Input PDF Snippet (Hypothetical)
"Patient Name: John Doe  
Date: 2025-07-10  
Diagnosis: Hypertension"

### Output JSON
```json
[
  {
    "segment": "Patient Name: John Doe",
    "metadata": {
      "type": "patient_info",
      "date": null,
      "provider": null
    }
  },
  {
    "segment": "Date: 2025-07-10",
    "metadata": {
      "type": "date",
      "date": "2025-07-10",
      "provider": null
    }
  },
  {
    "segment": "Diagnosis: Hypertension",
    "metadata": {
      "type": "diagnosis",
      "date": null,
      "provider": null
    }
  }
]
