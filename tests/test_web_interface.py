import json
from unittest.mock import ANY, MagicMock, Mock, patch

import pytest
import streamlit as st

from src.web_interface import WebInterface


@pytest.fixture
def web_interface():
    """Create a WebInterface instance for testing."""
    with patch("streamlit.session_state", MagicMock()):
        with patch("src.web_interface.PDFProcessor"):
            yield WebInterface()


class TestWebInterface:
    """Test the WebInterface class."""

    def test_session_state_initialization(self, web_interface):
        """Test session state initialization."""
        assert hasattr(st.session_state, "processing_results")
        assert hasattr(st.session_state, "batch_results")
        assert hasattr(st.session_state, "processing_status")

    @patch("streamlit.file_uploader")
    @patch("streamlit.info")
    @patch("streamlit.button")
    @patch("streamlit.columns")
    def test_single_document_page(
        self, mock_columns, mock_button, mock_info, mock_file_uploader, web_interface
    ):
        """Test single document page."""
        # Mock file uploader with a file
        mock_file = Mock()
        mock_file.name = "test.pdf"
        mock_file.size = 1024
        mock_file_uploader.return_value = mock_file

        # Mock columns
        mock_col1 = Mock()
        mock_col2 = Mock()
        mock_col1.__enter__ = Mock(return_value=None)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2.__enter__ = Mock(return_value=None)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_columns.return_value = [mock_col1, mock_col2]

        # Mock buttons
        mock_button.return_value = False

        # Test the page
        web_interface._single_document_page()

        mock_file_uploader.assert_called_once()
        mock_info.assert_called_once()
        assert mock_columns.call_count == 1
        assert mock_button.call_count == 2

    def test_process_single_document(self, web_interface):
        """Test processing a single document."""
        # Mock uploaded file
        mock_file = Mock()
        mock_file.name = "test.pdf"
        mock_file.size = 1024
        mock_file.read.return_value = b"PDF content"

        # Mock the processing result
        mock_result = {
            "document_id": "test-doc",
            "filename": "test.pdf",
            "page_count": 5,
            "segments": [{"text": "segment1", "type": "medical"}],
            "timeline": [{"date": "2023-01-01", "event": "event1"}],
        }

        with patch("streamlit.session_state", MagicMock()) as mock_session:
            st.session_state = mock_session
            with patch("streamlit.progress"):
                with patch("streamlit.empty"):
                    with patch("streamlit.rerun"):
                        with patch("tempfile.NamedTemporaryFile"):
                            with patch("builtins.open", mock_open_json(mock_result)):
                                web_interface._process_single_document(mock_file)

            mock_session.processing_results.__setitem__.assert_called_with("test.pdf", {"data": mock_result, "processed_at": ANY, "file_size": 1024, "processing_time": 0.0})
            mock_session.processing_status.__setitem__.assert_called_with("test.pdf", "completed")

    def test_display_document_summary(self, web_interface):
        """Test displaying document summary."""
        mock_data = {
            "document_id": "test-doc",
            "filename": "test.pdf",
            "page_count": 5,
            "segments": [
                {"text": "segment1", "type": "medical"},
                {"text": "segment2", "type": "diagnosis"},
            ],
            "processed_at": "2023-01-01T10:00:00",
        }

        with patch("streamlit.markdown") as mock_markdown:
            with patch("streamlit.columns") as mock_columns:
                with patch("streamlit.write") as mock_write:
                    # Mock columns
                    mock_col1 = Mock()
                    mock_col2 = Mock()
                    mock_col1.__enter__ = Mock(return_value=None)
                    mock_col1.__exit__ = Mock(return_value=None)
                    mock_col2.__enter__ = Mock(return_value=None)
                    mock_col2.__exit__ = Mock(return_value=None)
                    mock_columns.return_value = [mock_col1, mock_col2]

                    # Test the display
                    web_interface._display_document_summary(mock_data)

        assert mock_markdown.call_count > 0
        assert mock_columns.call_count > 0
        assert mock_write.call_count > 0

def mock_open_json(data):
    """Mock the open function for reading JSON."""
    from unittest.mock import mock_open

    mock_file = mock_open(read_data=json.dumps(data))
    mock_file.return_value.__enter__.return_value = mock_file.return_value
    return mock_file
