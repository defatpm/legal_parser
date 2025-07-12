"""Tests for the legacy web interface module."""

from unittest.mock import MagicMock, patch

import pytest
import streamlit as st

from src.web_interface import WebInterface


@pytest.fixture
def mock_session_state():
    """Mock session state."""
    st.session_state = MagicMock()
    st.session_state.processing_results = {}
    st.session_state.batch_results = {}
    st.session_state.processing_status = {}
    return st.session_state


@pytest.fixture
def web_interface(mock_session_state):
    """Create WebInterface instance with mocked dependencies."""
    with (
        patch("src.web_interface.get_config") as mock_get_config,
        patch("src.web_interface.PDFProcessor"),
    ):

        mock_get_config.return_value = {"max_file_size_mb": 10}
        yield WebInterface()


def test_web_interface_initialization(mock_session_state):
    """Test WebInterface initialization."""
    with (
        patch("src.web_interface.get_config") as mock_get_config,
        patch("src.web_interface.PDFProcessor") as mock_processor,
    ):

        mock_get_config.return_value = {"max_file_size_mb": 10}

        web_interface = WebInterface()

        assert web_interface.config is not None
        assert web_interface.processor is not None
        mock_get_config.assert_called_once()
        mock_processor.assert_called_once()


def test_single_document_page_method_exists(web_interface):
    """Test that _single_document_page method exists."""
    assert hasattr(web_interface, "_single_document_page")
    assert callable(web_interface._single_document_page)


def test_batch_processing_page_method_exists(web_interface):
    """Test that _batch_processing_page method exists."""
    assert hasattr(web_interface, "_batch_processing_page")
    assert callable(web_interface._batch_processing_page)


def test_processing_history_page_method_exists(web_interface):
    """Test that _processing_history_page method exists."""
    assert hasattr(web_interface, "_processing_history_page")
    assert callable(web_interface._processing_history_page)


def test_settings_page_method_exists(web_interface):
    """Test that _settings_page method exists."""
    assert hasattr(web_interface, "_settings_page")
    assert callable(web_interface._settings_page)


def test_process_single_document_method_exists(web_interface):
    """Test that _process_single_document method exists."""
    assert hasattr(web_interface, "_process_single_document")
    assert callable(web_interface._process_single_document)


def test_display_batch_results_method_exists(web_interface):
    """Test that _display_batch_results method exists."""
    assert hasattr(web_interface, "_display_batch_results")
    assert callable(web_interface._display_batch_results)


def test_create_batch_zip_method_exists(web_interface):
    """Test that _create_batch_zip method exists."""
    assert hasattr(web_interface, "_create_batch_zip")
    assert callable(web_interface._create_batch_zip)


def test_display_single_document_results_method_exists(web_interface):
    """Test that _display_single_document_results method exists."""
    assert hasattr(web_interface, "_display_single_document_results")
    assert callable(web_interface._display_single_document_results)


def test_display_document_summary_method_exists(web_interface):
    """Test that _display_document_summary method exists."""
    assert hasattr(web_interface, "_display_document_summary")
    assert callable(web_interface._display_document_summary)


def test_display_document_segments_method_exists(web_interface):
    """Test that _display_document_segments method exists."""
    assert hasattr(web_interface, "_display_document_segments")
    assert callable(web_interface._display_document_segments)


def test_display_document_timeline_method_exists(web_interface):
    """Test that _display_document_timeline method exists."""
    assert hasattr(web_interface, "_display_document_timeline")
    assert callable(web_interface._display_document_timeline)


def test_display_raw_json_method_exists(web_interface):
    """Test that _display_raw_json method exists."""
    assert hasattr(web_interface, "_display_raw_json")
    assert callable(web_interface._display_raw_json)


def test_display_export_options_method_exists(web_interface):
    """Test that _display_export_options method exists."""
    assert hasattr(web_interface, "_display_export_options")
    assert callable(web_interface._display_export_options)


def test_session_state_management(web_interface):
    """Test session state management."""
    # Test that session state is properly initialized
    assert hasattr(st.session_state, "processing_results")
    assert hasattr(st.session_state, "batch_results")
    assert hasattr(st.session_state, "processing_status")
