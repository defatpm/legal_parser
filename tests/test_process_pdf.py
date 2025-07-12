import json
from unittest.mock import MagicMock, patch

import pytest

from src.process_pdf import PDFProcessor
from tests.test_utils import ConcretePDFExtractor


@pytest.fixture
def sample_pdf_path(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.touch()
    return pdf_path


def test_process_pdf_no_mock(sample_pdf_path, tmp_path):
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


@patch("src.process_pdf.PDFProcessor")
def test_process_single_file(mock_pdf_processor, sample_pdf_path, tmp_path):
    import argparse

    from src.process_pdf import _process_single_file

    output_path = tmp_path / "output"
    args = argparse.Namespace(
        input=sample_pdf_path, output=output_path, verbose=False, batch=False
    )
    _process_single_file(args)
    mock_pdf_processor.return_value.process_pdf.assert_called_once_with(
        sample_pdf_path, output_path
    )


def test_process_batch(sample_pdf_path, tmp_path):
    import argparse

    from src.process_pdf import _process_batch

    output_path = tmp_path / "output"
    args = argparse.Namespace(
        input_dir=sample_pdf_path.parent,
        output=output_path,
        workers=None,
        progress=False,
        resume=False,
        resume_file=None,
        pattern="*.pdf",
        recursive=False,
        input=sample_pdf_path,
        csv_output=None,
        excel_output=None,
    )
    mock_batch_processor = MagicMock()
    mock_batch_processor.process_batch.return_value = MagicMock(
        total_jobs=1,
        successful_jobs=1,
        failed_jobs=0,
        average_duration=1.0,
        fastest_job=1.0,
        slowest_job=1.0,
        total_pages_processed=1,
        throughput_jobs_per_minute=1.0,
        throughput_pages_per_minute=1.0,
        memory_usage_mb=1.0,
        errors=[],
    )
    _process_batch(args, batch_processor=mock_batch_processor)
    mock_batch_processor.add_file.assert_called_once_with(
        sample_pdf_path, output_path / f"{sample_pdf_path.stem}.json"
    )
    mock_batch_processor.process_batch.assert_called_once()
