"""Tests for processor interface and base classes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.processors.base import (
    BaseProcessor,
    ProcessingContext,
    ProcessingResult,
    ProcessorMetadata,
    ProcessorRegistry,
    ProcessorStatus,
    get_processor_registry,
    register_processor,
)
from src.utils.exceptions import ValidationError
from tests.test_utils import ConcretePDFExtractor


class TestProcessorMetadata:
    """Tests for ProcessorMetadata class."""

    def test_metadata_creation(self):
        """Test creating processor metadata."""
        metadata = ProcessorMetadata(
            name="TestProcessor",
            version="1.0.0",
            description="Test processor",
            input_types=["str"],
            output_types=["dict"],
            capabilities=["test"],
            dependencies=["dep1", "dep2"],
        )

        assert metadata.name == "TestProcessor"
        assert metadata.version == "1.0.0"
        assert metadata.description == "Test processor"
        assert metadata.input_types == ["str"]
        assert metadata.output_types == ["dict"]
        assert metadata.capabilities == ["test"]
        assert metadata.dependencies == ["dep1", "dep2"]

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = ProcessorMetadata(
            name="TestProcessor",
            version="1.0.0",
            description="Test processor",
            input_types=["str"],
            output_types=["dict"],
        )

        metadata_dict = metadata.to_dict()

        assert metadata_dict["name"] == "TestProcessor"
        assert metadata_dict["version"] == "1.0.0"
        assert metadata_dict["description"] == "Test processor"
        assert metadata_dict["input_types"] == ["str"]
        assert metadata_dict["output_types"] == ["dict"]
        assert metadata_dict["capabilities"] == []
        assert metadata_dict["dependencies"] == []


class TestProcessingContext:
    """Tests for ProcessingContext class."""

    def test_context_creation(self):
        """Test creating processing context."""
        context = ProcessingContext(
            document_id="doc123",
            source_path="/path/to/file.pdf",
            processing_params={"param1": "value1"},
            metadata={"key": "value"},
        )

        assert context.document_id == "doc123"
        assert context.source_path == "/path/to/file.pdf"
        assert context.processing_params == {"param1": "value1"}
        assert context.metadata == {"key": "value"}

    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        context = ProcessingContext(
            document_id="doc123", source_path="/path/to/file.pdf"
        )

        context_dict = context.to_dict()

        assert context_dict["document_id"] == "doc123"
        assert context_dict["source_path"] == "/path/to/file.pdf"
        assert context_dict["processing_params"] == {}
        assert context_dict["metadata"] == {}


class TestProcessingResult:
    """Tests for ProcessingResult class."""

    def test_result_creation(self):
        """Test creating processing result."""
        result = ProcessingResult(
            status=ProcessorStatus.COMPLETED,
            output={"key": "value"},
            metadata={"meta": "data"},
            processing_time=1.5,
        )

        assert result.status == ProcessorStatus.COMPLETED
        assert result.output == {"key": "value"}
        assert result.metadata == {"meta": "data"}
        assert result.processing_time == 1.5
        assert result.error is None

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = ProcessingResult(
            status=ProcessorStatus.FAILED,
            output=None,
            error=ValueError("Test error"),
            processing_time=0.5,
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "failed"
        assert result_dict["output"] is None
        assert result_dict["error"] == "Test error"
        assert result_dict["processing_time"] == 0.5
        assert result_dict["metadata"] == {}


class MockProcessor(BaseProcessor):
    """Mock processor for testing."""

    def _apply_config_overrides(self):
        pass

    def _validate_processor_config(self):
        pass

    @property
    def metadata(self) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="MockProcessor",
            version="1.0.0",
            description="Mock processor for testing",
            input_types=["str"],
            output_types=["str"],
            capabilities=["mock", "test"],
        )

    def process(
        self, input_data: Any, context: ProcessingContext | None = None
    ) -> ProcessingResult:
        context = self._update_processing_context(context)

        if input_data == "error":
            error = ValueError("Mock error")
            return self._create_error_result(error)

        output = f"processed_{input_data}"
        return self._create_success_result(output, {"processed": True})

    def _validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, str) and input_data != "invalid"


class TestBaseProcessor:
    """Tests for BaseProcessor class."""

    def test_processor_initialization(self):
        """Test processor initialization."""
        processor = MockProcessor()

        assert processor.status == ProcessorStatus.IDLE
        assert processor.processing_context is None
        assert processor.processing_stats == {}
        assert processor.config is not None
        assert processor.error_handler is not None

    def test_processor_can_process(self):
        """Test can_process method."""
        processor = MockProcessor()

        assert processor.can_process("valid_input") is True
        assert processor.can_process("invalid") is False
        assert processor.can_process(123) is False

    def test_processor_process_success(self):
        """Test successful processing."""
        processor = MockProcessor()

        result = processor.process("test_input")

        assert result.status == ProcessorStatus.COMPLETED
        assert result.output == "processed_test_input"
        assert result.metadata["processed"] is True
        assert result.error is None

    def test_processor_process_error(self):
        """Test error processing."""
        processor = MockProcessor()

        result = processor.process("error")

        assert result.status == ProcessorStatus.FAILED
        assert result.output is None
        assert result.error is not None
        assert isinstance(result.error, ValueError)

    def test_processor_process_with_context(self):
        """Test processing with context."""
        processor = MockProcessor()
        context = ProcessingContext(
            document_id="doc123", processing_params={"param1": "value1"}
        )

        result = processor.process("test_input", context)

        assert result.status == ProcessorStatus.COMPLETED
        assert processor.processing_context is not None
        assert processor.processing_context.document_id == "doc123"
        assert (
            processor.processing_context.metadata["processor_name"] == "MockProcessor"
        )

    def test_processor_get_stats(self):
        """Test getting processing statistics."""
        processor = MockProcessor()

        stats = processor.get_processing_stats()

        assert stats["status"] == "idle"
        assert stats["metadata"]["name"] == "MockProcessor"
        assert "stats" in stats
        assert "error_summary" in stats

    def test_processor_reset_stats(self):
        """Test resetting statistics."""
        processor = MockProcessor()
        processor.processing_stats["test"] = "value"

        processor.reset_stats()

        assert processor.processing_stats == {}
        assert processor.status == ProcessorStatus.IDLE


class TestProcessorRegistry:
    """Tests for ProcessorRegistry class."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = ProcessorRegistry()

        assert registry._processors == {}
        assert registry._instances == {}

    def test_register_processor(self):
        """Test registering a processor."""
        registry = ProcessorRegistry()

        registry.register(MockProcessor)

        assert "MockProcessor" in registry._processors
        assert registry._processors["MockProcessor"] == MockProcessor

    def test_register_invalid_processor(self):
        """Test registering invalid processor."""
        registry = ProcessorRegistry()

        with pytest.raises(ValueError, match="must inherit from BaseProcessor"):
            registry.register(str)  # Invalid processor class

    def test_get_processor(self):
        """Test getting processor instance."""
        registry = ProcessorRegistry()
        registry.register(MockProcessor)

        processor = registry.get_processor("MockProcessor")

        assert isinstance(processor, MockProcessor)
        assert processor.metadata.name == "MockProcessor"

    def test_get_nonexistent_processor(self):
        """Test getting non-existent processor."""
        registry = ProcessorRegistry()

        with pytest.raises(KeyError, match="Processor 'NonExistent' not found"):
            registry.get_processor("NonExistent")

    def test_list_processors(self):
        """Test listing processors."""
        registry = ProcessorRegistry()
        registry.register(MockProcessor)

        processors = registry.list_processors()

        assert len(processors) == 1
        assert processors[0].name == "MockProcessor"

    def test_get_processors_by_capability(self):
        """Test getting processors by capability."""
        registry = ProcessorRegistry()
        registry.register(MockProcessor)

        processors = registry.get_processors_by_capability("test")

        assert len(processors) == 1
        assert processors[0] == "MockProcessor"

        processors = registry.get_processors_by_capability("nonexistent")

        assert len(processors) == 0

    def test_clear_registry(self):
        """Test clearing registry."""
        registry = ProcessorRegistry()
        registry.register(MockProcessor)

        registry.clear()

        assert registry._processors == {}
        assert registry._instances == {}


class TestPDFExtractorInterface:
    """Tests for PDFExtractor processor interface."""

    def test_pdf_extractor_metadata(self):
        """Test PDFExtractor metadata."""
        extractor = ConcretePDFExtractor()
        metadata = extractor.metadata

        assert metadata.name == "PDFExtractor"
        assert metadata.version == "1.0.0"
        assert "text_extraction" in metadata.capabilities
        assert "ocr" in metadata.capabilities
        assert "pdf_processing" in metadata.capabilities
        assert "PyMuPDF" in metadata.dependencies

    def test_pdf_extractor_can_process(self):
        """Test PDFExtractor can_process method."""
        extractor = ConcretePDFExtractor()

        # Create a temporary PDF file for testing
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4\n%Test PDF content\n")
            tmp_path = Path(tmp.name)

        try:
            assert extractor.can_process(str(tmp_path)) is True
            assert extractor.can_process(tmp_path) is True
            assert extractor.can_process("nonexistent.pdf") is False
            assert extractor.can_process("file.txt") is False
        finally:
            tmp_path.unlink()

    def test_pdf_extractor_process_nonexistent_file(self):
        """Test PDFExtractor with non-existent file."""
        extractor = ConcretePDFExtractor()

        result = extractor.process("nonexistent.pdf")

        assert result.status == ProcessorStatus.FAILED
        assert result.error is not None
        assert result.output is None

    def test_pdf_extractor_process_invalid_input(self):
        """Test PDFExtractor with invalid input."""
        extractor = ConcretePDFExtractor()

        result = extractor.process(123)

        assert result.status == ProcessorStatus.FAILED
        assert result.error is not None
        assert isinstance(result.error, ValidationError)

    def test_pdf_extractor_get_stats(self):
        """Test PDFExtractor statistics."""
        extractor = ConcretePDFExtractor()

        stats = extractor.get_processing_stats()

        assert stats["status"] == "idle"
        assert stats["metadata"]["name"] == "PDFExtractor"
        assert "capabilities" in stats["metadata"]
        assert "text_extraction" in stats["metadata"]["capabilities"]


class TestGlobalRegistry:
    """Tests for global processor registry."""

    def test_global_registry_access(self):
        """Test accessing global registry."""
        registry = get_processor_registry()
        registry.register(ConcretePDFExtractor)

        assert isinstance(registry, ProcessorRegistry)
        # PDF extractor should be registered by default
        assert "PDFExtractor" in registry._processors

    def test_register_processor_function(self):
        """Test global register_processor function."""
        # Clear registry first
        registry = get_processor_registry()
        initial_count = len(registry._processors)

        register_processor(MockProcessor)

        assert len(registry._processors) == initial_count + 1
        assert "MockProcessor" in registry._processors
