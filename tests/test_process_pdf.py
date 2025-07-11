import json

import pytest

from src.process_pdf import PDFProcessor


@pytest.fixture
def sample_pdf(tmp_path):
    # Create a mock PDF (for testing, use a real small PDF in actual repo)
    pdf_path = tmp_path / "sample.pdf"
    # Mock content (in real test, write a PDF file here)
    return str(pdf_path)


def test_process_pdf(sample_pdf, tmp_path):
    output_path = tmp_path / "output.json"
    processor = PDFProcessor(sample_pdf, str(output_path))
    # Mock extraction for test (override methods if needed)
    processor.process()
    assert output_path.exists()
    with open(output_path) as f:
        data = json.load(f)
    assert isinstance(data, list)
    # Add more assertions based on expected output
