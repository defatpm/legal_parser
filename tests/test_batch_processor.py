"""Tests for the batch processor module."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.batch_processor import BatchJob, BatchProcessor, BatchProgress, BatchStatistics


class TestBatchJob:
    """Test the BatchJob class."""

    def test_batch_job_creation(self):
        """Test creating a batch job."""
        job = BatchJob(
            id="test-job", input_path=Path("test.pdf"), output_path=Path("test.json")
        )

        assert job.id == "test-job"
        assert job.input_path == Path("test.pdf")
        assert job.output_path == Path("test.json")
        assert job.status == "pending"
        assert job.duration is None

    def test_batch_job_duration(self):
        """Test duration calculation."""
        from datetime import datetime

        job = BatchJob(
            id="test-job", input_path=Path("test.pdf"), output_path=Path("test.json")
        )

        # Set start and end times
        job.start_time = datetime(2023, 1, 1, 10, 0, 0)
        job.end_time = datetime(2023, 1, 1, 10, 0, 30)

        assert job.duration == 30.0  # 30 seconds


class TestBatchProgress:
    """Test the BatchProgress class."""

    def test_batch_progress_creation(self):
        """Test creating batch progress."""
        progress = BatchProgress(total_jobs=10)

        assert progress.total_jobs == 10
        assert progress.completed_jobs == 0
        assert progress.failed_jobs == 0
        assert progress.processing_jobs == 0
        assert progress.pending_jobs == 10

    def test_batch_progress_rates(self):
        """Test progress rate calculations."""
        progress = BatchProgress(
            total_jobs=10, completed_jobs=7, failed_jobs=2, processing_jobs=1
        )

        assert progress.pending_jobs == 0
        assert progress.completion_rate == 70.0
        assert progress.failure_rate == 20.0
        assert not progress.is_complete

    def test_batch_progress_completion(self):
        """Test completion detection."""
        progress = BatchProgress(total_jobs=10, completed_jobs=8, failed_jobs=2)

        assert progress.is_complete

    def test_batch_progress_eta(self):
        """Test ETA calculation."""
        from datetime import datetime, timedelta

        progress = BatchProgress(
            total_jobs=10, completed_jobs=5, failed_jobs=0, processing_jobs=1
        )

        # Set start time to 10 minutes ago
        progress.start_time = datetime.now() - timedelta(minutes=10)

        eta = progress.eta_seconds
        assert eta is not None
        assert eta > 0  # Should have some time remaining


class TestBatchProcessor:
    """Test the BatchProcessor class."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "input"
            output_dir = temp_path / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            yield {"temp": temp_path, "input": input_dir, "output": output_dir}

    @pytest.fixture
    def sample_pdf_files(self, temp_dirs):
        """Create sample PDF files for testing."""
        input_dir = temp_dirs["input"]

        # Create sample PDF files (empty files for testing)
        pdf_files = []
        for i in range(5):
            pdf_file = input_dir / f"sample_{i}.pdf"
            pdf_file.write_text(f"Sample PDF content {i}")
            pdf_files.append(pdf_file)

        # Create subdirectory with more files
        subdir = input_dir / "subdir"
        subdir.mkdir()
        for i in range(3):
            pdf_file = subdir / f"sub_sample_{i}.pdf"
            pdf_file.write_text(f"Sub sample PDF content {i}")
            pdf_files.append(pdf_file)

        return pdf_files

    def test_batch_processor_creation(self):
        """Test creating a batch processor."""
        processor = BatchProcessor(max_workers=4)

        assert processor.max_workers == 4
        assert len(processor.jobs) == 0
        assert processor.progress.total_jobs == 0

    def test_add_file(self, temp_dirs):
        """Test adding a single file to batch."""
        processor = BatchProcessor()

        input_file = temp_dirs["input"] / "test.pdf"
        output_file = temp_dirs["output"] / "test.json"
        input_file.write_text("test content")

        processor.add_file(input_file, output_file)

        assert len(processor.jobs) == 1
        assert processor.jobs[0].input_path == input_file
        assert processor.jobs[0].output_path == output_file
        assert processor.progress.total_jobs == 1

    def test_add_file_not_found(self, temp_dirs):
        """Test adding a file that doesn't exist."""
        processor = BatchProcessor()

        input_file = temp_dirs["input"] / "nonexistent.pdf"
        output_file = temp_dirs["output"] / "test.json"

        with pytest.raises(FileNotFoundError):
            processor.add_file(input_file, output_file)

    def test_add_directory(self, temp_dirs, sample_pdf_files):
        """Test adding files from a directory."""
        processor = BatchProcessor()

        processor.add_directory(
            input_dir=temp_dirs["input"],
            output_dir=temp_dirs["output"],
            recursive=False,
        )

        # Should find 5 files in root directory (not recursive)
        assert len(processor.jobs) == 5
        assert processor.progress.total_jobs == 5

    def test_add_directory_recursive(self, temp_dirs, sample_pdf_files):
        """Test adding files from a directory recursively."""
        processor = BatchProcessor()

        processor.add_directory(
            input_dir=temp_dirs["input"], output_dir=temp_dirs["output"], recursive=True
        )

        # Should find 8 files total (5 in root + 3 in subdir)
        assert len(processor.jobs) == 8
        assert processor.progress.total_jobs == 8

    def test_add_directory_pattern(self, temp_dirs):
        """Test adding files with a specific pattern."""
        processor = BatchProcessor()

        # Create files with different extensions
        (temp_dirs["input"] / "file1.pdf").write_text("content")
        (temp_dirs["input"] / "file2.pdf").write_text("content")
        (temp_dirs["input"] / "file3.txt").write_text("content")

        processor.add_directory(
            input_dir=temp_dirs["input"],
            output_dir=temp_dirs["output"],
            pattern="*.pdf",
        )

        # Should only find PDF files
        assert len(processor.jobs) == 2

    def test_add_directory_not_found(self, temp_dirs):
        """Test adding from a directory that doesn't exist."""
        processor = BatchProcessor()

        nonexistent_dir = temp_dirs["temp"] / "nonexistent"

        with pytest.raises(FileNotFoundError):
            processor.add_directory(
                input_dir=nonexistent_dir, output_dir=temp_dirs["output"]
            )

    @patch("src.batch_processor.PDFProcessor")
    def test_process_batch_success(self, mock_pdf_processor, temp_dirs):
        """Test successful batch processing."""
        # Mock the PDF processor
        mock_processor_instance = Mock()
        mock_pdf_processor.return_value = mock_processor_instance

        # Mock successful processing
        def mock_process_pdf(input_path, output_path):
            # Create mock output file
            output_path.write_text(
                json.dumps(
                    {
                        "page_count": 5,
                        "segments": [{"text": "segment1"}, {"text": "segment2"}],
                        "timeline": [{"event": "event1"}],
                    }
                )
            )
            return output_path

        mock_processor_instance.process_pdf.side_effect = mock_process_pdf

        # Create batch processor
        processor = BatchProcessor(max_workers=2)

        # Add test files
        for i in range(3):
            input_file = temp_dirs["input"] / f"test_{i}.pdf"
            output_file = temp_dirs["output"] / f"test_{i}.json"
            input_file.write_text(f"content {i}")
            processor.add_file(input_file, output_file)

        # Process batch
        statistics = processor.process_batch()

        # Verify results
        assert statistics.total_jobs == 3
        assert statistics.successful_jobs == 3
        assert statistics.failed_jobs == 0
        assert statistics.total_pages_processed == 15  # 5 pages * 3 files
        assert len(statistics.errors) == 0

        # Verify all jobs completed
        for job in processor.jobs:
            assert job.status == "completed"
            assert job.result is not None

    @patch("src.batch_processor.PDFProcessor")
    def test_process_batch_with_failures(self, mock_pdf_processor, temp_dirs):
        """Test batch processing with some failures."""
        # Mock the PDF processor
        mock_processor_instance = Mock()
        mock_pdf_processor.return_value = mock_processor_instance

        # Mock processing with some failures
        def mock_process_pdf(input_path, output_path):
            if "fail" in input_path.name:
                raise Exception("Processing failed")

            # Create mock output file for successful cases
            output_path.write_text(
                json.dumps(
                    {
                        "page_count": 3,
                        "segments": [{"text": "segment1"}],
                        "timeline": [{"event": "event1"}],
                    }
                )
            )
            return output_path

        mock_processor_instance.process_pdf.side_effect = mock_process_pdf

        # Create batch processor
        processor = BatchProcessor(max_workers=2)

        # Add test files (some will fail)
        for i in range(5):
            name = f"test_fail_{i}.pdf" if i % 2 == 0 else f"test_success_{i}.pdf"
            input_file = temp_dirs["input"] / name
            output_file = temp_dirs["output"] / f"test_{i}.json"
            input_file.write_text(f"content {i}")
            processor.add_file(input_file, output_file)

        # Process batch
        statistics = processor.process_batch()

        # Verify results
        assert statistics.total_jobs == 5
        assert statistics.successful_jobs == 2  # Only success files
        assert statistics.failed_jobs == 3  # Only fail files
        assert len(statistics.errors) == 3

        # Verify job statuses
        successful_jobs = [job for job in processor.jobs if job.status == "completed"]
        failed_jobs = [job for job in processor.jobs if job.status == "failed"]

        assert len(successful_jobs) == 2
        assert len(failed_jobs) == 3

    def test_process_batch_empty(self):
        """Test processing an empty batch."""
        processor = BatchProcessor()

        with pytest.raises(ValueError, match="No jobs to process"):
            processor.process_batch()

    def test_get_job_status(self, temp_dirs):
        """Test getting job status."""
        processor = BatchProcessor()

        input_file = temp_dirs["input"] / "test.pdf"
        output_file = temp_dirs["output"] / "test.json"
        input_file.write_text("content")

        processor.add_file(input_file, output_file)
        job_id = processor.jobs[0].id

        # Get job status
        job = processor.get_job_status(job_id)
        assert job is not None
        assert job.id == job_id

        # Test non-existent job
        missing_job = processor.get_job_status("nonexistent")
        assert missing_job is None

    def test_get_failed_jobs(self, temp_dirs):
        """Test getting failed jobs."""
        processor = BatchProcessor()

        # Create some jobs with different statuses
        for i, status in enumerate(["pending", "completed", "failed", "failed"]):
            input_file = temp_dirs["input"] / f"test_{i}.pdf"
            output_file = temp_dirs["output"] / f"test_{i}.json"
            input_file.write_text(f"content {i}")

            processor.add_file(input_file, output_file)
            processor.jobs[i].status = status

        failed_jobs = processor.get_failed_jobs()
        assert len(failed_jobs) == 2
        assert all(job.status == "failed" for job in failed_jobs)

    def test_progress_callback(self, temp_dirs):
        """Test progress callback functionality."""
        callback_calls = []

        def progress_callback(progress):
            callback_calls.append(progress.completed_jobs)

        processor = BatchProcessor(progress_callback=progress_callback)

        # Add a file
        input_file = temp_dirs["input"] / "test.pdf"
        output_file = temp_dirs["output"] / "test.json"
        input_file.write_text("content")
        processor.add_file(input_file, output_file)

        # Mock the processing to be very fast
        with patch("src.batch_processor.PDFProcessor") as mock_pdf_processor:
            mock_processor_instance = Mock()
            mock_pdf_processor.return_value = mock_processor_instance

            def mock_process_pdf(input_path, output_path):
                output_path.write_text(
                    json.dumps({"page_count": 1, "segments": [], "timeline": []})
                )
                return output_path

            mock_processor_instance.process_pdf.side_effect = mock_process_pdf

            processor.process_batch()

        # Verify callback was called
        assert len(callback_calls) > 0
        assert callback_calls[-1] == 1  # Final callback should show 1 completed job

    def test_resume_functionality(self, temp_dirs):
        """Test resume functionality."""
        processor = BatchProcessor()

        # Set resume file
        resume_file = temp_dirs["temp"] / "resume.json"
        processor.set_resume_file(resume_file)

        # Add some jobs
        for i in range(3):
            input_file = temp_dirs["input"] / f"test_{i}.pdf"
            output_file = temp_dirs["output"] / f"test_{i}.json"
            input_file.write_text(f"content {i}")
            processor.add_file(input_file, output_file)

        # Simulate some completed jobs
        processor.jobs[0].status = "completed"
        processor.jobs[1].status = "failed"
        processor.jobs[2].status = "pending"

        processor.progress.completed_jobs = 1
        processor.progress.failed_jobs = 1

        # Save resume state
        processor._save_resume_state()

        # Verify resume file exists
        assert resume_file.exists()

        # Create new processor and load resume state
        new_processor = BatchProcessor()
        new_processor.set_resume_file(resume_file)
        new_processor._load_resume_state()

        # Verify state was loaded correctly
        assert len(new_processor.jobs) == 3
        assert new_processor.progress.completed_jobs == 1
        assert new_processor.progress.failed_jobs == 1
        assert new_processor.jobs[0].status == "completed"
        assert new_processor.jobs[1].status == "failed"
        assert new_processor.jobs[2].status == "pending"


class TestBatchStatistics:
    """Test the BatchStatistics class."""

    def test_batch_statistics_creation(self):
        """Test creating batch statistics."""
        stats = BatchStatistics(
            total_jobs=10,
            successful_jobs=8,
            failed_jobs=2,
            total_duration=300.0,
            average_duration=30.0,
            fastest_job=15.0,
            slowest_job=60.0,
            total_pages_processed=100,
            average_pages_per_job=10.0,
            throughput_jobs_per_minute=1.6,
            throughput_pages_per_minute=16.0,
            memory_usage_mb=256.0,
            errors=["Error 1", "Error 2"],
        )

        assert stats.total_jobs == 10
        assert stats.successful_jobs == 8
        assert stats.failed_jobs == 2
        assert stats.total_duration == 300.0
        assert stats.average_duration == 30.0
        assert stats.fastest_job == 15.0
        assert stats.slowest_job == 60.0
        assert stats.total_pages_processed == 100
        assert stats.average_pages_per_job == 10.0
        assert stats.throughput_jobs_per_minute == 1.6
        assert stats.throughput_pages_per_minute == 16.0
        assert stats.memory_usage_mb == 256.0
        assert len(stats.errors) == 2


class TestBatchProcessorIntegration:
    """Integration tests for batch processor."""

    def test_end_to_end_workflow(self, temp_dirs):
        """Test complete end-to-end batch processing workflow."""
        # This test would require actual PDF processing
        # For now, we'll mock it but structure it as a real workflow

        with patch("src.batch_processor.PDFProcessor") as mock_pdf_processor:
            # Setup mock
            mock_processor_instance = Mock()
            mock_pdf_processor.return_value = mock_processor_instance

            def mock_process_pdf(input_path, output_path):
                # Simulate processing time
                time.sleep(0.01)

                # Create realistic output
                output_path.write_text(
                    json.dumps(
                        {
                            "document_id": "test-doc",
                            "filename": input_path.name,
                            "page_count": 5,
                            "segments": [
                                {"text": "Sample segment", "type": "medical"},
                                {"text": "Another segment", "type": "diagnosis"},
                            ],
                            "timeline": [
                                {"date": "2023-01-01", "event": "Event 1"},
                                {"date": "2023-01-02", "event": "Event 2"},
                            ],
                        }
                    )
                )
                return output_path

            mock_processor_instance.process_pdf.side_effect = mock_process_pdf

            # Create test files
            for i in range(5):
                pdf_file = temp_dirs["input"] / f"medical_record_{i}.pdf"
                pdf_file.write_text(f"Medical record content {i}")

            # Setup batch processor
            processor = BatchProcessor(max_workers=2)
            processor.add_directory(
                input_dir=temp_dirs["input"], output_dir=temp_dirs["output"]
            )

            # Process batch
            statistics = processor.process_batch()

            # Verify results
            assert statistics.total_jobs == 5
            assert statistics.successful_jobs == 5
            assert statistics.failed_jobs == 0
            assert statistics.total_pages_processed == 25  # 5 pages * 5 files

            # Verify output files were created
            for i in range(5):
                output_file = temp_dirs["output"] / f"medical_record_{i}.json"
                assert output_file.exists()

                # Verify content
                with open(output_file) as f:
                    data = json.load(f)
                    assert data["page_count"] == 5
                    assert len(data["segments"]) == 2
                    assert len(data["timeline"]) == 2


if __name__ == "__main__":
    pytest.main([__file__])
