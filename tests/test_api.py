"""Tests for the REST API."""

from __future__ import annotations

import io
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models import ProcessingRequest, ProcessingStatus
from src.api.tasks import TaskInfo, TaskManager
from src.processors.base import get_processor_registry
from tests.test_utils import ConcretePDFExtractor

# Test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def register_test_processor():
    """Register a test processor for the API tests."""
    registry = get_processor_registry()
    registry.register(ConcretePDFExtractor)
    yield
    registry.clear()


@pytest.fixture
def mock_pdf_file():
    """Create a mock PDF file for testing."""
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    return io.BytesIO(content)


@pytest.fixture
def processing_request():
    """Create a processing request for testing."""
    return ProcessingRequest(
        ocr_enabled=True,
        ocr_language="eng",
        normalize_whitespace=True,
        min_text_length=10,
        output_format="json",
        include_metadata=True,
    )


class TestAPIEndpoints:
    """Tests for API endpoints."""

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["version"] == "1.0.0"
        assert "features" in data
        assert "endpoints" in data
        assert "PDF Processing" in data["features"]

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "uptime" in data
        assert "memory_usage_mb" in data

    def test_processors_endpoint(self):
        """Test processors listing endpoint."""
        response = client.get("/processors")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Should have at least the PDF extractor
        pdf_processor = next((p for p in data if p["name"] == "PDFExtractor"), None)
        assert pdf_processor is not None
        assert pdf_processor["version"] == "1.0.0"
        assert "text_extraction" in pdf_processor["capabilities"]

    def test_config_endpoint(self):
        """Test configuration endpoint."""
        response = client.get("/config")
        assert response.status_code == 200

        data = response.json()
        assert "max_file_size_mb" in data
        assert "ocr_enabled" in data
        assert "supported_formats" in data
        assert "pdf" in data["supported_formats"]

    def test_queue_endpoint(self):
        """Test queue status endpoint."""
        response = client.get("/queue")
        assert response.status_code == 200

        data = response.json()
        assert "queue_size" in data
        assert "processing_tasks" in data
        assert "active_workers" in data
        assert "max_workers" in data

    def test_stats_endpoint(self):
        """Test statistics endpoint."""
        response = client.get("/stats")
        assert response.status_code == 200

        data = response.json()
        assert "total_requests" in data
        assert "completed_requests" in data
        assert "failed_requests" in data
        assert "average_processing_time" in data

    def test_metrics_endpoint(self):
        """Test system metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_upload_valid_file(self, mock_pdf_file):
        """Test uploading a valid PDF file."""
        files = {"file": ("test.pdf", mock_pdf_file, "application/pdf")}

        response = client.post("/upload", files=files)
        assert response.status_code == 200

        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["size_bytes"] > 0
        assert data["content_type"] == "application/pdf"
        assert "upload_id" in data
        assert "expires_at" in data

    def test_upload_invalid_file(self):
        """Test uploading an invalid file."""
        files = {"file": ("test.txt", io.BytesIO(b"Not a PDF"), "text/plain")}

        response = client.post("/upload", files=files)
        assert response.status_code == 400

        data = response.json()
        assert "error" in data
        assert "PDF files" in data["message"]

    def test_process_document(self, mock_pdf_file):
        """Test processing a document."""
        files = {"file": ("test.pdf", mock_pdf_file, "application/pdf")}
        data = {
            "ocr_enabled": True,
            "ocr_language": "eng",
            "normalize_whitespace": True,
            "min_text_length": 10,
            "output_format": "json",
            "include_metadata": True,
        }

        response = client.post("/process", files=files, data=data)
        assert response.status_code == 200

        response_data = response.json()
        assert "task_id" in response_data
        assert response_data["status"] == "pending"
        assert response_data["message"] == "Document submitted for processing"

    def test_get_task_status_not_found(self):
        """Test getting status of non-existent task."""
        response = client.get("/status/nonexistent-task-id")
        assert response.status_code == 404

        data = response.json()
        assert "Task not found" in data["message"]

    def test_get_task_result_not_found(self):
        """Test getting result of non-existent task."""
        response = client.get("/result/nonexistent-task-id")
        assert response.status_code == 404

        data = response.json()
        assert "Task not found" in data["message"]

    def test_cancel_task_not_found(self):
        """Test cancelling non-existent task."""
        response = client.delete("/task/nonexistent-task-id")
        assert response.status_code == 400

        data = response.json()
        assert "Task cannot be cancelled" in data["message"]


class TestProcessingModels:
    """Tests for processing models."""

    def test_processing_request_validation(self):
        """Test processing request validation."""
        # Valid request
        request = ProcessingRequest(
            ocr_enabled=True,
            ocr_language="eng",
            normalize_whitespace=True,
            min_text_length=10,
            output_format="json",
            include_metadata=True,
        )

        assert request.ocr_enabled is True
        assert request.ocr_language == "eng"
        assert request.output_format == "json"

    def test_processing_request_invalid_language(self):
        """Test processing request with invalid language."""
        with pytest.raises(ValueError, match="Invalid OCR language"):
            ProcessingRequest(ocr_language="invalid")

    def test_processing_request_invalid_format(self):
        """Test processing request with invalid format."""
        with pytest.raises(ValueError, match="Invalid output format"):
            ProcessingRequest(output_format="invalid")

    def test_processing_status_enum(self):
        """Test processing status enum."""
        assert ProcessingStatus.PENDING == "pending"
        assert ProcessingStatus.PROCESSING == "processing"
        assert ProcessingStatus.COMPLETED == "completed"
        assert ProcessingStatus.FAILED == "failed"
        assert ProcessingStatus.CANCELLED == "cancelled"


class TestTaskManager:
    """Tests for task manager."""

    @pytest.fixture
    def task_manager(self):
        """Create a task manager for testing."""
        return TaskManager(max_concurrent_tasks=2)

    @pytest.fixture
    def mock_file_path(self):
        """Create a mock file path."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4\nTest content")
            return Path(tmp.name)

    def test_task_manager_initialization(self, task_manager):
        """Test task manager initialization."""
        assert task_manager.max_concurrent_tasks == 2
        assert task_manager.tasks == {}
        assert task_manager.active_tasks == {}
        assert task_manager.running is False

    @pytest.mark.asyncio
    async def test_task_submission(
        self, task_manager, mock_file_path, processing_request
    ):
        """Test task submission."""
        task_id = await task_manager.submit_task(
            "test.pdf", mock_file_path, processing_request
        )

        assert task_id in task_manager.tasks
        task_info = task_manager.tasks[task_id]
        assert task_info.filename == "test.pdf"
        assert task_info.file_path == mock_file_path
        assert task_info.status == ProcessingStatus.PENDING

        # Cleanup
        mock_file_path.unlink()

    @pytest.mark.asyncio
    async def test_task_status_retrieval(
        self, task_manager, mock_file_path, processing_request
    ):
        """Test task status retrieval."""
        task_id = await task_manager.submit_task(
            "test.pdf", mock_file_path, processing_request
        )

        task_info = await task_manager.get_task_status(task_id)
        assert task_info is not None
        assert task_info.task_id == task_id
        assert task_info.status == ProcessingStatus.PENDING

        # Test non-existent task
        non_existent = await task_manager.get_task_status("nonexistent")
        assert non_existent is None

        # Cleanup
        mock_file_path.unlink()

    @pytest.mark.asyncio
    async def test_task_cancellation(
        self, task_manager, mock_file_path, processing_request
    ):
        """Test task cancellation."""
        task_id = await task_manager.submit_task(
            "test.pdf", mock_file_path, processing_request
        )

        # Cancel task
        success = await task_manager.cancel_task(task_id)
        assert success is True

        # Check task status
        task_info = await task_manager.get_task_status(task_id)
        assert task_info.status == ProcessingStatus.CANCELLED

        # Try to cancel again
        success = await task_manager.cancel_task(task_id)
        assert success is False

        # Cleanup
        mock_file_path.unlink()

    @pytest.mark.asyncio
    async def test_queue_status(self, task_manager, mock_file_path, processing_request):
        """Test queue status."""
        # Submit some tasks
        await task_manager.submit_task("test1.pdf", mock_file_path, processing_request)
        await task_manager.submit_task("test2.pdf", mock_file_path, processing_request)

        queue_status = await task_manager.get_queue_status()

        assert queue_status["queue_size"] >= 2
        assert queue_status["max_workers"] == 2
        assert "total_processed" in queue_status
        assert "uptime_seconds" in queue_status

        # Cleanup
        mock_file_path.unlink()

    @pytest.mark.asyncio
    async def test_statistics(self, task_manager):
        """Test statistics retrieval."""
        stats = await task_manager.get_statistics()

        assert "total_requests" in stats
        assert "completed_requests" in stats
        assert "failed_requests" in stats
        assert "average_processing_time" in stats
        assert "total_pages_processed" in stats

    @pytest.mark.asyncio
    async def test_cleanup_old_tasks(
        self, task_manager, mock_file_path, processing_request
    ):
        """Test cleanup of old tasks."""
        # Submit and cancel a task
        task_id = await task_manager.submit_task(
            "test.pdf", mock_file_path, processing_request
        )
        await task_manager.cancel_task(task_id)

        # Initially task should exist
        assert task_id in task_manager.tasks

        # Cleanup with 0 hours (should remove all completed tasks)
        await task_manager.cleanup_old_tasks(0)

        # Task should be removed
        assert task_id not in task_manager.tasks

        # Cleanup
        mock_file_path.unlink()


class TestTaskInfo:
    """Tests for TaskInfo class."""

    def test_task_info_creation(self, processing_request):
        """Test task info creation."""
        task_info = TaskInfo(
            task_id="test-task-id",
            filename="test.pdf",
            file_path=Path("test.pdf"),
            request=processing_request,
            status=ProcessingStatus.PENDING,
            created_at=datetime.now(),
        )

        assert task_info.task_id == "test-task-id"
        assert task_info.filename == "test.pdf"
        assert task_info.status == ProcessingStatus.PENDING
        assert task_info.progress == 0.0

    def test_task_info_to_dict(self, processing_request):
        """Test task info dictionary conversion."""
        from datetime import datetime

        task_info = TaskInfo(
            task_id="test-task-id",
            filename="test.pdf",
            file_path=Path("test.pdf"),
            request=processing_request,
            status=ProcessingStatus.COMPLETED,
            created_at=datetime.now(),
            progress=1.0,
            processing_time=5.0,
        )

        task_dict = task_info.to_dict()

        assert task_dict["task_id"] == "test-task-id"
        assert task_dict["filename"] == "test.pdf"
        assert task_dict["status"] == "completed"
        assert task_dict["progress"] == 1.0
        assert task_dict["processing_time"] == 5.0


class TestErrorHandling:
    """Tests for error handling."""

    def test_validation_error_handling(self):
        """Test validation error handling."""
        # Test invalid file upload
        files = {"file": ("test.txt", io.BytesIO(b"Not a PDF"), "text/plain")}

        response = client.post("/upload", files=files)
        assert response.status_code == 400

        data = response.json()
        assert "error" in data
        assert data["error"] == "ValidationError" or "PDF files" in data["message"]

    def test_not_found_error_handling(self):
        """Test 404 error handling."""
        response = client.get("/status/nonexistent-task")
        assert response.status_code == 404

        data = response.json()
        assert "error" in data
        assert "Task not found" in data["message"]

    def test_invalid_endpoint(self):
        """Test invalid endpoint."""
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404


class TestIntegration:
    """Integration tests for the API."""

    @pytest.mark.asyncio
    async def test_full_processing_workflow(self, mock_pdf_file):
        """Test the complete processing workflow."""
        # This test would require a real PDF file and actual processing
        # For now, we'll test the API endpoints without actual processing

        # Upload file
        files = {"file": ("test.pdf", mock_pdf_file, "application/pdf")}
        upload_response = client.post("/upload", files=files)
        assert upload_response.status_code == 200

        upload_data = upload_response.json()
        upload_id = upload_data["upload_id"]

        # Process uploaded file
        process_data = {
            "ocr_enabled": True,
            "ocr_language": "eng",
            "normalize_whitespace": True,
            "min_text_length": 10,
            "output_format": "json",
            "include_metadata": True,
        }

        process_response = client.post(f"/process/{upload_id}", json=process_data)
        assert process_response.status_code == 200

        process_data = process_response.json()
        task_id = process_data["task_id"]

        # Check task status
        status_response = client.get(f"/status/{task_id}")
        assert status_response.status_code == 200

        status_data = status_response.json()
        assert status_data["task_id"] == task_id
        assert status_data["status"] in ["pending", "processing", "completed", "failed"]


@patch("uvicorn.run")
def test_main(mock_run):
    from src.api.main import main

    main()
    mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan():
    from fastapi import FastAPI

    from src.api.main import lifespan

    app = FastAPI()

    async with lifespan(app):
        assert app.state.limiter is not None


@pytest.mark.asyncio
async def test_cleanup_old_files(tmp_path):
    import time

    from src.api.main import cleanup_old_files, upload_dir

    # Create a dummy file
    dummy_file = upload_dir / "dummy.pdf"
    dummy_file.touch()

    # Make the file old
    old_time = time.time() - 25 * 3600
    import os

    os.utime(dummy_file, (old_time, old_time))

    await cleanup_old_files()

    assert not dummy_file.exists()
