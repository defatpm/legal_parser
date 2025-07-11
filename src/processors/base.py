"""Abstract base class for all document processors."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from ..utils.config import get_config
from ..utils.error_handler import get_error_handler

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ProcessorStatus(Enum):
    """Status of a processor."""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProcessorMetadata:
    """Metadata about a processor."""
    name: str
    version: str
    description: str
    input_types: list[str]
    output_types: list[str]
    capabilities: list[str] = field(default_factory=list)
    configuration_schema: dict[str, Any] | None = None
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "input_types": self.input_types,
            "output_types": self.output_types,
            "capabilities": self.capabilities,
            "configuration_schema": self.configuration_schema,
            "dependencies": self.dependencies
        }


@dataclass
class ProcessingContext:
    """Context information for processing operations."""
    document_id: str | None = None
    source_path: str | None = None
    processing_params: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "document_id": self.document_id,
            "source_path": self.source_path,
            "processing_params": self.processing_params,
            "metadata": self.metadata
        }


@dataclass
class ProcessingResult:
    """Result of a processing operation."""
    status: ProcessorStatus
    output: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    error: Exception | None = None
    processing_time: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "status": self.status.value,
            "output": self.output,
            "metadata": self.metadata,
            "error": str(self.error) if self.error else None,
            "processing_time": self.processing_time
        }


class BaseProcessor(ABC):
    """Abstract base class for all document processors."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the processor.

        Args:
            config: Optional configuration dictionary
        """
        self.config = get_config()
        self.error_handler = get_error_handler()
        self.logger = logging.getLogger(self.__class__.__name__)
        # Override with provided config if available
        if config:
            self._apply_config_overrides(config)
        # Initialize processor-specific state
        self.status = ProcessorStatus.IDLE
        self.processing_context: ProcessingContext | None = None
        self.processing_stats: dict[str, Any] = {}
        # Validate processor configuration
        self._validate_configuration()

    @property
    @abstractmethod
    def metadata(self) -> ProcessorMetadata:
        """Get processor metadata.

        Returns:
            ProcessorMetadata object describing this processor
        """
        pass

    @abstractmethod
    def process(self, input_data: Any, context: ProcessingContext | None = None) -> ProcessingResult:
        """Process input data.

        Args:
            input_data: Data to process
            context: Optional processing context

        Returns:
            ProcessingResult with output and metadata
        """
        pass

    def can_process(self, input_data: Any) -> bool:
        """Check if this processor can handle the input data.

        Args:
            input_data: Data to check

        Returns:
            True if processor can handle the data, False otherwise
        """
        try:
            return self._validate_input(input_data)
        except Exception as e:
            self.logger.debug(f"Input validation failed: {e}")
            return False

    def get_processing_stats(self) -> dict[str, Any]:
        """Get processing statistics.

        Returns:
            Dictionary of processing statistics
        """
        return {
            "status": self.status.value,
            "metadata": self.metadata.to_dict(),
            "stats": self.processing_stats.copy(),
            "error_summary": self.error_handler.get_error_summary()
        }

    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self.processing_stats.clear()
        self.error_handler.reset_error_counts()
        self.status = ProcessorStatus.IDLE

    @abstractmethod
    def _apply_config_overrides(self, config: dict[str, Any]) -> None:
        """Apply configuration overrides.

        Args:
            config: Configuration dictionary
        """
        # This method can be overridden by subclasses to handle
        # processor-specific configuration
        pass

    def _validate_configuration(self) -> None:
        """Validate processor configuration.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        from ..utils.exceptions import ConfigurationError
        # Check if required configuration sections exist
        required_sections = self._get_required_config_sections()
        for section in required_sections:
            if not hasattr(self.config, section):
                raise ConfigurationError(
                    f"Required configuration section '{section}' not found"
                )
        # Additional validation can be implemented by subclasses
        self._validate_processor_config()

    def _get_required_config_sections(self) -> list[str]:
        """Get list of required configuration sections.

        Returns:
            List of required configuration section names
        """
        # Default implementation - can be overridden by subclasses
        return []

    @abstractmethod
    def _validate_processor_config(self) -> None:
        """Validate processor-specific configuration.

        This method should be overridden by subclasses to implement
        processor-specific configuration validation.
        """
        pass

    def _validate_input(self, input_data: Any) -> bool:
        """Validate input data.

        Args:
            input_data: Data to validate

        Returns:
            True if input is valid, False otherwise
        """
        # Default implementation - should be overridden by subclasses
        return input_data is not None

    def _update_processing_context(self, context: ProcessingContext | None) -> ProcessingContext:
        """Update and return processing context.

        Args:
            context: Optional context to update

        Returns:
            Updated processing context
        """
        if context is None:
            context = ProcessingContext()
        # Add processor-specific metadata
        context.metadata.update({
            "processor_name": self.metadata.name,
            "processor_version": self.metadata.version,
            "processor_capabilities": self.metadata.capabilities
        })
        self.processing_context = context
        return context

    def _create_success_result(self, output: Any, metadata: dict[str, Any] | None = None,
                              processing_time: float | None = None) -> ProcessingResult:
        """Create a successful processing result.

        Args:
            output: Processing output
            metadata: Optional metadata
            processing_time: Optional processing time

        Returns:
            ProcessingResult with success status
        """
        return ProcessingResult(
            status=ProcessorStatus.COMPLETED,
            output=output,
            metadata=metadata or {},
            processing_time=processing_time
        )

    def _create_error_result(self, error: Exception, processing_time: float | None = None) -> ProcessingResult:
        """Create an error processing result.

        Args:
            error: Exception that occurred
            processing_time: Optional processing time

        Returns:
            ProcessingResult with error status
        """
        return ProcessingResult(
            status=ProcessorStatus.FAILED,
            output=None,
            error=error,
            processing_time=processing_time
        )


class ProcessorRegistry:
    """Registry for managing processors."""

    def __init__(self):
        """Initialize the registry."""
        self._processors: dict[str, type[BaseProcessor]] = {}
        self._instances: dict[str, BaseProcessor] = {}

    def register(self, processor_class: type[BaseProcessor]) -> None:
        """Register a processor class.

        Args:
            processor_class: Processor class to register
        """
        if not issubclass(processor_class, BaseProcessor):
            raise ValueError("Processor class must inherit from BaseProcessor")
        # Create temporary instance to get metadata
        temp_instance = processor_class()
        name = temp_instance.metadata.name
        self._processors[name] = processor_class
        logger.info(f"Registered processor: {name}")

    def get_processor(self, name: str, config: dict[str, Any] | None = None) -> BaseProcessor:
        """Get a processor instance.

        Args:
            name: Processor name
            config: Optional configuration

        Returns:
            Processor instance

        Raises:
            KeyError: If processor not found
        """
        if name not in self._processors:
            raise KeyError(f"Processor '{name}' not found")
        # Create new instance if not cached or config provided
        cache_key = f"{name}_{hash(str(config))}"
        if cache_key not in self._instances or config is not None:
            self._instances[cache_key] = self._processors[name](config)
        return self._instances[cache_key]

    def list_processors(self) -> list[ProcessorMetadata]:
        """List all registered processors.

        Returns:
            List of processor metadata
        """
        metadata_list = []
        for processor_class in self._processors.values():
            temp_instance = processor_class()
            metadata_list.append(temp_instance.metadata)
        return metadata_list

    def get_processors_by_capability(self, capability: str) -> list[str]:
        """Get processors that have a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of processor names
        """
        matching_processors = []
        for processor_class in self._processors.values():
            temp_instance = processor_class()
            if capability in temp_instance.metadata.capabilities:
                matching_processors.append(temp_instance.metadata.name)
        return matching_processors

    def clear(self) -> None:
        """Clear the registry."""
        self._processors.clear()
        self._instances.clear()


# Global processor registry
_processor_registry = ProcessorRegistry()


def get_processor_registry() -> ProcessorRegistry:
    """Get the global processor registry.

    Returns:
        Global processor registry
    """
    return _processor_registry


def register_processor(processor_class: type[BaseProcessor]) -> None:
    """Register a processor class with the global registry.

    Args:
        processor_class: Processor class to register
    """
    _processor_registry.register(processor_class)
