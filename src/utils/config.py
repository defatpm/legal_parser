"""Configuration management for the medical record processor."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .logging import JSONFormatter

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration."""

    name: str = "Medical Record Pre-Processor"
    version: str = "0.1.0"
    debug: bool = False


@dataclass
class ProcessingConfig:
    """Processing configuration."""

    max_file_size_mb: int = 100
    timeout: dict[str, int] = field(
        default_factory=lambda: {
            "pdf_extraction": 300,
            "segmentation": 180,
            "metadata_extraction": 120,
            "timeline_building": 60,
        }
    )
    memory: dict[str, int | bool] = field(
        default_factory=lambda: {
            "max_memory_per_doc_mb": 512,
            "enable_monitoring": True,
        }
    )


@dataclass
class PDFExtractionConfig:
    """PDF extraction configuration."""

    ocr: dict[str, bool | str | int] = field(
        default_factory=lambda: {
            "enabled": True,
            "language": "eng",
            "confidence_threshold": 60,
            "dpi": 300,
        }
    )
    text: dict[str, bool | int] = field(
        default_factory=lambda: {
            "normalize_whitespace": True,
            "remove_headers_footers": True,
            "min_text_length": 10,
        }
    )


@dataclass
class SegmentationConfig:
    """Document segmentation configuration."""

    strategy: str = "keyword"
    keywords: dict[str, list] = field(
        default_factory=lambda: {
            "medical_sections": [
                "patient history",
                "diagnosis",
                "treatment",
                "medications",
                "laboratory results",
                "imaging",
                "procedure notes",
                "discharge summary",
            ],
            "date_patterns": [
                r"\\d{1,2}/\\d{1,2}/\\d{4}",
                r"\\d{4}-\\d{2}-\\d{2}",
                r"\\b\\w+\\s+\\d{1,2},\\s+\\d{4}\\b",
            ],
        }
    )
    min_segment_length: int = 50
    max_segment_length: int = 2000


@dataclass
class MetadataExtractionConfig:
    """Metadata extraction configuration."""

    entities: dict[str, bool | list] = field(
        default_factory=lambda: {
            "enabled": True,
            "types": ["PERSON", "DATE", "ORG", "GPE", "TIME"],
        }
    )
    dates: dict[str, list | str] = field(
        default_factory=lambda: {
            "formats": ["%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"],
            "default_timezone": "UTC",
        }
    )
    providers: dict[str, list] = field(
        default_factory=lambda: {
            "titles": ["Dr.", "Doctor", "Physician", "Nurse", "PA", "NP", "MD", "DO"]
        }
    )


@dataclass
class TimelineConfig:
    """Timeline building configuration."""

    sort_order: str = "chronological"
    grouping: dict[str, bool | str] = field(
        default_factory=lambda: {"enabled": True, "period": "day"}
    )
    include_confidence: bool = True


@dataclass
class OutputConfig:
    """Output configuration."""

    default_format: str = "json"
    json: dict[str, bool | int] = field(
        default_factory=lambda: {
            "pretty_print": True,
            "indent": 2,
            "ensure_ascii": False,
        }
    )
    csv: dict[str, str | bool] = field(
        default_factory=lambda: {
            "delimiter": ",",
            "quote_char": '"',
            "include_headers": True,
        }
    )
    naming: dict[str, bool | str] = field(
        default_factory=lambda: {
            "include_timestamp": False,
            "template": "{stem}_processed",
        }
    )


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: dict[str, bool | str | int] = field(
        default_factory=lambda: {
            "enabled": False,
            "path": "logs/processor.log",
            "max_size_mb": 10,
            "backup_count": 5,
        }
    )
    structured: dict[str, bool | str] = field(
        default_factory=lambda: {"enabled": False, "format": "json"}
    )


@dataclass
class SecurityConfig:
    """Security configuration."""

    validation: dict[str, int | list | bool] = field(
        default_factory=lambda: {
            "max_filename_length": 255,
            "allowed_extensions": [".pdf"],
            "malware_scan": False,
        }
    )
    temp_files: dict[str, bool | int] = field(
        default_factory=lambda: {
            "auto_cleanup": True,
            "cleanup_interval": 3600,
            "max_age": 86400,
        }
    )


@dataclass
class PerformanceConfig:
    """Performance configuration."""

    parallel: dict[str, bool | int] = field(
        default_factory=lambda: {"enabled": True, "workers": 0, "chunk_size": 10}
    )
    cache: dict[str, bool | str | int] = field(
        default_factory=lambda: {
            "enabled": True,
            "type": "memory",
            "ttl": 3600,
            "max_size_mb": 128,
        }
    )


@dataclass
class Config:
    """Main configuration class."""

    app: AppConfig = field(default_factory=AppConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    pdf_extraction: PDFExtractionConfig = field(default_factory=PDFExtractionConfig)
    segmentation: SegmentationConfig = field(default_factory=SegmentationConfig)
    metadata_extraction: MetadataExtractionConfig = field(
        default_factory=MetadataExtractionConfig
    )
    timeline: TimelineConfig = field(default_factory=TimelineConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)


class ConfigManager:
    """Configuration manager for loading and validating configuration."""

    def __init__(self, config_path: str | Path | None = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses default locations.
        """
        self.config_path = self._resolve_config_path(config_path)
        self._config: Config | None = None

    def _resolve_config_path(self, config_path: str | Path | None) -> Path:
        """Resolve configuration file path.

        Args:
            config_path: User-provided config path or None

        Returns:
            Path to configuration file
        """
        # Check environment variable first
        env_path = os.getenv("MEDICAL_PROCESSOR_CONFIG")
        if env_path:
            return Path(env_path)
        if config_path:
            return Path(config_path)
        # Check default locations
        default_locations = [
            Path.cwd() / "config.yaml",
            Path.cwd() / "config.yml",
            Path.home() / ".medical-processor" / "config.yaml",
            Path("/etc/medical-processor/config.yaml"),
        ]
        for path in default_locations:
            if path.exists():
                return path
        # Return default location for creation
        return Path.cwd() / "config.yaml"

    def load_config(self) -> Config:
        """Load configuration from file.

        Returns:
            Configuration object

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
            ValueError: If config validation fails
        """
        if self._config is not None:
            return self._config
        if not self.config_path.exists():
            logger.warning(
                f"Config file not found at {self.config_path}, using defaults"
            )
            self._config = Config()
            return self._config
        logger.info(f"Loading configuration from {self.config_path}")
        try:
            with open(self.config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            if not config_data:
                logger.warning("Empty configuration file, using defaults")
                self._config = Config()
                return self._config
            # Build configuration object from loaded data
            self._config = self._build_config_from_dict(config_data)
            self._validate_config(self._config)
            # Set up logging
            setup_logging(self._config.logging)
            logger.info("Configuration loaded successfully")
            return self._config
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in config file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise

    def _build_config_from_dict(self, config_data: dict[str, Any]) -> Config:
        """Build configuration object from dictionary.

        Args:
            config_data: Configuration data from YAML

        Returns:
            Configuration object
        """
        config = Config()
        # Update each configuration section
        if "app" in config_data:
            config.app = AppConfig(**config_data.get("app", {}))
        if "processing" in config_data:
            config.processing = ProcessingConfig(**config_data.get("processing", {}))
        if "pdf_extraction" in config_data:
            config.pdf_extraction = PDFExtractionConfig(**config_data.get("pdf_extraction", {}))
        if "segmentation" in config_data:
            config.segmentation = SegmentationConfig(**config_data.get("segmentation", {}))
        if "metadata_extraction" in config_data:
            config.metadata_extraction = MetadataExtractionConfig(
                **config_data.get("metadata_extraction", {})
            )
        if "timeline" in config_data:
            config.timeline = TimelineConfig(**config_data.get("timeline", {}))
        if "output" in config_data:
            config.output = OutputConfig(**config_data.get("output", {}))
        if "logging" in config_data:
            config.logging = LoggingConfig(**config_data.get("logging", {}))
        if "security" in config_data:
            config.security = SecurityConfig(**config_data.get("security", {}))
        if "performance" in config_data:
            config.performance = PerformanceConfig(**config_data.get("performance", {}))
        return config

    def _validate_config(self, config: Config) -> None:
        """Validate configuration values.

        Args:
            config: Configuration object to validate

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate file size limits
        if config.processing.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")
        # Validate timeout values
        for name, timeout in config.processing.timeout.items():
            if timeout <= 0:
                raise ValueError(f"Timeout {name} must be positive")
        # Validate log level
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if config.logging.level not in valid_levels:
            raise ValueError(f"Invalid log level: {config.logging.level}")
        # Validate segmentation strategy
        valid_strategies = {"keyword", "ml", "hybrid"}
        if config.segmentation.strategy not in valid_strategies:
            raise ValueError(
                f"Invalid segmentation strategy: {config.segmentation.strategy}"
            )
        # Validate output format
        valid_formats = {"json", "csv", "excel"}
        if config.output.default_format not in valid_formats:
            raise ValueError(f"Invalid output format: {config.output.default_format}")
        logger.debug("Configuration validation passed")

    def get_config(self) -> Config:
        """Get current configuration, loading if necessary.

        Returns:
            Configuration object
        """
        if self._config is None:
            return self.load_config()
        return self._config

    def reload_config(self) -> Config:
        """Reload configuration from file.

        Returns:
            Configuration object
        """
        self._config = None
        return self.load_config()


def setup_logging(config: LoggingConfig) -> None:
    """Set up logging based on configuration."""
    root_logger = logging.getLogger()
    root_logger.setLevel(config.level)
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    # Create new handler
    handler: logging.Handler
    if config.file["enabled"]:
        from logging.handlers import RotatingFileHandler

        log_path = Path(config.file["path"])
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_path,
            maxBytes=int(config.file["max_size_mb"]) * 1024 * 1024,
            backupCount=int(config.file["backup_count"]),
        )
    else:
        handler = logging.StreamHandler()
    # Set formatter
    if config.structured["enabled"]:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(config.format)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


# Global configuration instance
_config_manager: ConfigManager | None = None


def get_config() -> Config:
    """Get global configuration instance.

    Returns:
        Configuration object
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.get_config()


def set_config_path(config_path: str | Path) -> None:
    """Set configuration file path.

    Args:
        config_path: Path to configuration file
    """
    global _config_manager
    _config_manager = ConfigManager(config_path)


def reload_config() -> Config:
    """Reload configuration from file.

    Returns:
        Configuration object
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.reload_config()
