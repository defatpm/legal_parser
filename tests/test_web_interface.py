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

            mock_session.processing_results.__setitem__.assert_called_with(
                "test.pdf",
                {
                    "data": mock_result,
                    "processed_at": ANY,
                    "file_size": 1024,
                    "processing_time": 0.0,
                },
            )
            mock_session.processing_status.__setitem__.assert_called_with(
                "test.pdf", "completed"
            )

    def test_display_document_summary(self, web_interface):
        """Test _display_document_summary function."""
        data = {
            "document_id": "test_id",
            "filename": "test.pdf",
            "page_count": 1,
            "segments": [{"type": "medical", "text": "segment1"}],
            "processed_at": "2023-01-01T00:00:00",
        }
        mock_col1 = Mock()
        mock_col1.__enter__ = Mock(return_value=None)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = Mock()
        mock_col2.__enter__ = Mock(return_value=None)
        mock_col2.__exit__ = Mock(return_value=None)
        with (
            patch("streamlit.markdown"),
            patch("streamlit.columns", return_value=(mock_col1, mock_col2)),
            patch("streamlit.write"),
        ):
            web_interface._display_document_summary(data)

    def test_display_document_segments(self, web_interface):
        """Test _display_document_segments function."""
        data = {
            "segments": [
                {"type": "medical", "text": "segment1"},
                {"type": "diagnosis", "text": "segment2"},
            ]
        }
        mock_col1 = Mock()
        mock_col1.__enter__ = Mock(return_value=None)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = Mock()
        mock_col2.__enter__ = Mock(return_value=None)
        mock_col2.__exit__ = Mock(return_value=None)
        with (
            patch("streamlit.markdown"),
            patch("streamlit.columns", return_value=(mock_col1, mock_col2)),
            patch("streamlit.multiselect"),
            patch("streamlit.slider"),
            patch("streamlit.expander"),
            patch("streamlit.write"),
            patch("streamlit.text_area"),
            patch("streamlit.json"),
        ):
            web_interface._display_document_segments(data)

    def test_display_document_timeline(self, web_interface):
        """Test _display_document_timeline function."""
        data = {
            "timeline": [
                {"date": "2023-01-01", "event": "event1"},
                {"date": "2023-01-02", "event": "event2"},
            ]
        }
        with (
            patch("streamlit.markdown"),
            patch("pandas.DataFrame"),
            patch("streamlit.dataframe"),
            patch("streamlit.line_chart"),
        ):
            web_interface._display_document_timeline(data)

    def test_display_raw_json(self, web_interface):
        """Test _display_raw_json function."""
        data = {"key": "value"}
        with (
            patch("streamlit.markdown"),
            patch("streamlit.code"),
            patch("streamlit.download_button"),
        ):
            web_interface._display_raw_json(data)

    def test_batch_processing_page(self, web_interface):
        """Test _batch_processing_page function."""
        mock_col1 = Mock()
        mock_col1.__enter__ = Mock(return_value=None)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = Mock()
        mock_col2.__enter__ = Mock(return_value=None)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_col3 = Mock()
        mock_col3.__enter__ = Mock(return_value=None)
        mock_col3.__exit__ = Mock(return_value=None)
        with (
            patch("streamlit.markdown"),
            patch("streamlit.file_uploader") as mock_file_uploader,
            patch("streamlit.info"),
            patch("streamlit.expander"),
            patch("streamlit.columns", return_value=(mock_col1, mock_col2, mock_col3)),
            patch("streamlit.slider"),
            patch("streamlit.checkbox"),
            patch("streamlit.button"),
        ):
            mock_file = Mock()
            mock_file.name = "test.pdf"
            mock_file.size = 1024
            mock_file_uploader.return_value = [mock_file]
            web_interface._batch_processing_page()

    def test_settings_page(self, web_interface):
        """Test _settings_page function."""
        mock_col1 = Mock()
        mock_col1.__enter__ = Mock(return_value=None)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = Mock()
        mock_col2.__enter__ = Mock(return_value=None)
        mock_col2.__exit__ = Mock(return_value=None)
        with (
            patch("streamlit.markdown"),
            patch("streamlit.expander"),
            patch("streamlit.json"),
            patch("streamlit.columns", return_value=(mock_col1, mock_col2)),
            patch("streamlit.info"),
        ):
            web_interface._settings_page()


class TestWebInterfaceHelpers:
    """Test the helper functions in WebInterface."""

    def test_create_batch_zip(self, web_interface):
        """Test _create_batch_zip function."""
        results = [
            {
                "status": "completed",
                "filename": "test1.pdf",
                "data": {
                    "segments": [
                        {
                            "document_type": "medical",
                            "text": "segment1",
                            "segment_id": "1",
                            "text_content": "segment1",
                            "page_start": 1,
                            "page_end": 1,
                        }
                    ],
                    "timeline": [{"date": "2023-01-01", "event": "event1"}],
                },
            },
            {
                "status": "completed",
                "filename": "test2.pdf",
                "data": {
                    "segments": [
                        {
                            "document_type": "diagnosis",
                            "text": "segment2",
                            "segment_id": "2",
                            "text_content": "segment2",
                            "page_start": 1,
                            "page_end": 1,
                        }
                    ],
                    "timeline": [{"date": "2023-01-02", "event": "event2"}],
                },
            },
            {"status": "error", "filename": "test3.pdf"},
        ]
        zip_data = web_interface._create_batch_zip(results)
        assert isinstance(zip_data, bytes)
        assert len(zip_data) > 0


def mock_open_json(data):
    """Mock the open function for reading JSON."""
    from unittest.mock import mock_open

    mock_file = mock_open(read_data=json.dumps(data))
    mock_file.return_value.__enter__.return_value = mock_file.return_value
    return mock_file
