"""Tests for configuration management."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.utils.config import Config, ConfigManager, get_config


class TestConfigManager:
    """Tests for ConfigManager class."""

    def test_load_default_config(self):
        """Test loading default configuration."""
        config = Config()

        # Check default values
        assert config.app.name == "Medical Record Pre-Processor"
        assert config.app.version == "0.1.0"
        assert config.processing.max_file_size_mb == 100
        assert config.pdf_extraction.ocr["enabled"] is True
        assert config.segmentation.strategy == "keyword"
        assert config.output.default_format == "json"

    def test_load_config_from_file(self):
        """Test loading configuration from YAML file."""
        # Create temporary config file
        config_data = {
            "app": {"name": "Test Processor", "version": "1.0.0", "debug": True},
            "processing": {"max_file_size_mb": 200},
            "pdf_extraction": {"ocr": {"enabled": False, "language": "spa"}},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            manager = ConfigManager(temp_path)
            config = manager.load_config()

            # Check loaded values
            assert config.app.name == "Test Processor"
            assert config.app.version == "1.0.0"
            assert config.app.debug is True
            assert config.processing.max_file_size_mb == 200
            assert config.pdf_extraction.ocr["enabled"] is False
            assert config.pdf_extraction.ocr["language"] == "spa"

            # Check defaults are preserved
            assert config.segmentation.strategy == "keyword"
            assert config.output.default_format == "json"

        finally:
            temp_path.unlink()

    def test_config_validation(self):
        """Test configuration validation."""
        # Test invalid file size
        config_data = {"processing": {"max_file_size_mb": -1}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            manager = ConfigManager(temp_path)
            with pytest.raises(ValueError, match="max_file_size_mb must be positive"):
                manager.load_config()
        finally:
            temp_path.unlink()

    def test_invalid_yaml_file(self):
        """Test handling of invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)

        try:
            manager = ConfigManager(temp_path)
            with pytest.raises(yaml.YAMLError):
                manager.load_config()
        finally:
            temp_path.unlink()

    def test_missing_config_file(self):
        """Test handling of missing config file."""
        non_existent_path = Path("/tmp/non_existent_config.yaml")
        manager = ConfigManager(non_existent_path)

        # Should return default config without raising error
        config = manager.load_config()
        assert config.app.name == "Medical Record Pre-Processor"

    def test_config_caching(self):
        """Test that configuration is cached."""
        manager = ConfigManager()

        # First load
        config1 = manager.load_config()

        # Second load should return same instance
        config2 = manager.get_config()
        assert config1 is config2

    def test_config_reload(self):
        """Test configuration reload functionality."""
        config_data = {"app": {"name": "Original Name"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            manager = ConfigManager(temp_path)
            config1 = manager.load_config()
            assert config1.app.name == "Original Name"

            # Update config file
            config_data["app"]["name"] = "Updated Name"
            with open(temp_path, "w") as f:
                yaml.dump(config_data, f)

            # Reload should pick up changes
            config2 = manager.reload_config()
            assert config2.app.name == "Updated Name"

        finally:
            temp_path.unlink()

    def test_environment_variable_config_path(self):
        """Test using environment variable for config path."""
        config_data = {"app": {"name": "Env Config"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            with patch.dict("os.environ", {"MEDICAL_PROCESSOR_CONFIG": str(temp_path)}):
                manager = ConfigManager()
                config = manager.load_config()
                assert config.app.name == "Env Config"
        finally:
            temp_path.unlink()


class TestGlobalConfig:
    """Tests for global configuration functions."""

    def test_get_config_singleton(self):
        """Test global config singleton behavior."""
        config1 = get_config()
        config2 = get_config()

        # Should be same instance
        assert config1 is config2

    def test_set_config_path(self):
        """Test setting global config path."""
        from src.utils.config import set_config_path

        config_data = {"app": {"name": "Global Config Test"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            set_config_path(temp_path)
            config = get_config()
            assert config.app.name == "Global Config Test"
        finally:
            temp_path.unlink()


class TestConfigDataclasses:
    """Tests for configuration dataclasses."""

    def test_app_config_defaults(self):
        """Test AppConfig default values."""
        from src.utils.config import AppConfig

        config = AppConfig()
        assert config.name == "Medical Record Pre-Processor"
        assert config.version == "0.1.0"
        assert config.debug is False

    def test_processing_config_defaults(self):
        """Test ProcessingConfig default values."""
        from src.utils.config import ProcessingConfig

        config = ProcessingConfig()
        assert config.max_file_size_mb == 100
        assert "pdf_extraction" in config.timeout
        assert config.timeout["pdf_extraction"] == 300
        assert config.memory["max_memory_per_doc_mb"] == 512

    def test_pdf_extraction_config_defaults(self):
        """Test PDFExtractionConfig default values."""
        from src.utils.config import PDFExtractionConfig

        config = PDFExtractionConfig()
        assert config.ocr["enabled"] is True
        assert config.ocr["language"] == "eng"
        assert config.ocr["confidence_threshold"] == 60
        assert config.text["normalize_whitespace"] is True

    def test_segmentation_config_defaults(self):
        """Test SegmentationConfig default values."""
        from src.utils.config import SegmentationConfig

        config = SegmentationConfig()
        assert config.strategy == "keyword"
        assert "patient history" in config.keywords["medical_sections"]
        assert config.min_segment_length == 50
        assert config.max_segment_length == 2000

    def test_output_config_defaults(self):
        """Test OutputConfig default values."""
        from src.utils.config import OutputConfig

        config = OutputConfig()
        assert config.default_format == "json"
        assert config.json["pretty_print"] is True
        assert config.json["indent"] == 2
        assert config.csv["delimiter"] == ","
        assert config.naming["template"] == "{stem}_processed"
