import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.process_pdf import PDFProcessor
from tests.test_utils import ConcretePDFExtractor


@pytest.fixture
def sample_pdf(tmp_path):
    # Create a mock PDF (for testing, use a real small PDF in actual repo)
    pdf_path = tmp_path / "sample.pdf"
    # Mock content (in real test, write a PDF file here)
    return str(pdf_path)


def test_process_pdf(sample_pdf, tmp_path):
    output_path = tmp_path / "output.json"
    processor = PDFProcessor(extractor=ConcretePDFExtractor())
    # Mock extraction for test (override methods if needed)
    with patch.object(processor, 'extractor') as mock_extractor:
        mock_extractor.extract_pages.return_value = []
        processor.process_pdf(Path(sample_pdf), output_path)
    assert output_path.exists()
    with open(output_path) as f:
        data = json.load(f)
    assert isinstance(data, dict)
    # Add more assertions based on expected output
