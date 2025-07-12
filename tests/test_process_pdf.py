import json
from unittest.mock import MagicMock, patch

import pytest

from src.process_pdf import PDFProcessor, main
from tests.test_utils import ConcretePDFExtractor


@pytest.fixture
def sample_pdf_path(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.touch()
    return pdf_path


def test_process_pdf(sample_pdf_path, tmp_path):
    output_path = tmp_path / "output.json"
    processor = PDFProcessor(extractor=ConcretePDFExtractor())

    with (
        patch.object(processor.extractor, "extract_pages", return_value=[]),
        patch.object(processor.segmenter, "segment_document", return_value=[]),
        patch.object(processor.metadata_extractor, "extract_metadata", return_value=[]),
        patch.object(
            processor.timeline_builder,
            "build_timeline",
            return_value=MagicMock(to_dict=lambda: {}),
        ),
    ):
        result_path = processor.process_pdf(sample_pdf_path, output_path)

        assert result_path == output_path
        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)


@patch("src.process_pdf._process_single_file")
def test_main_single_file(mock_process_single, sample_pdf_path):
    with (
        patch("sys.argv", ["prog", "--input", str(sample_pdf_path)]),
        pytest.raises(SystemExit) as e,
    ):
        main()
    assert e.type is SystemExit
    mock_process_single.assert_called_once()


@patch("src.process_pdf._process_batch")
def test_main_batch_file(mock_process_batch, sample_pdf_path):
    with (
        patch("sys.argv", ["prog", "--input", str(sample_pdf_path), "--batch"]),
        pytest.raises(SystemExit) as e,
    ):
        main()
    assert e.type is SystemExit
    mock_process_batch.assert_called_once()
