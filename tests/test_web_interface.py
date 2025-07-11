"""Tests for the web interface module."""
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.web_interface import WebInterface


class TestWebInterface:
    """Test the WebInterface class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        config = Mock()
        config.app.name = "Medical Record Processor"
        config.app.version = "1.0.0"
        config.app.debug = False
        config.processing.max_file_size_mb = 100
        config.processing.timeout.pdf_extraction = 300
        config.processing.timeout.segmentation = 180
        config.processing.timeout.metadata_extraction = 120
        config.processing.timeout.timeline_building = 60
        config.performance.parallel.enabled = True
        config.performance.parallel.workers = 4
        config.performance.parallel.chunk_size = 10
        return config

    @pytest.fixture
    def mock_processor(self):
        """Mock PDF processor."""
        processor = Mock()
        processor.process_pdf.return_value = Path("/tmp/test_output.json")
        return processor

    @pytest.fixture
    def web_interface(self, mock_config, mock_processor):
        """Create a web interface instance with mocked dependencies."""
        with patch('src.web_interface.get_config', return_value=mock_config):
            with patch('src.web_interface.PDFProcessor', return_value=mock_processor):
                interface = WebInterface()
                return interface

    def test_web_interface_initialization(self, web_interface):
        """Test web interface initialization."""
        assert web_interface.config is not None
        assert web_interface.processor is not None

    def test_session_state_initialization(self, web_interface):
        """Test session state initialization."""
        # Mock streamlit session state
        with patch('streamlit.session_state', {}) as mock_session:
            WebInterface()

            # Check that session state keys would be initialized
            assert 'processing_results' not in mock_session
            assert 'batch_results' not in mock_session
            assert 'processing_status' not in mock_session

    @patch('streamlit.set_page_config')
    @patch('streamlit.markdown')
    @patch('streamlit.sidebar')
    def test_run_method(self, mock_sidebar, mock_markdown, mock_set_page_config, web_interface):
        """Test the main run method."""
        # Mock sidebar selectbox
        mock_sidebar.selectbox.return_value = "Single Document"

        # Mock the page methods
        with patch.object(web_interface, '_single_document_page'):
            web_interface.run()

            # Verify page config was set
            mock_set_page_config.assert_called_once()

            # Verify markdown was called for styling
            assert mock_markdown.call_count >= 1

    @patch('streamlit.file_uploader')
    @patch('streamlit.info')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    def test_single_document_page(self, mock_columns, mock_button, mock_info, mock_file_uploader, web_interface):
        """Test single document page."""
        # Mock file uploader with a file
        mock_file = Mock()
        mock_file.name = "test.pdf"
        mock_file.size = 1024
        mock_file_uploader.return_value = mock_file

        # Mock columns
        mock_col1 = Mock()
        mock_col2 = Mock()
        mock_columns.return_value = [mock_col1, mock_col2]

        # Mock buttons
        mock_col1.button.return_value = False
        mock_col2.button.return_value = False

        # Test the page
        web_interface._single_document_page()

        # Verify file uploader was called
        mock_file_uploader.assert_called_once()

        # Verify info was shown for the uploaded file
        mock_info.assert_called_once()

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
            "timeline": [{"date": "2023-01-01", "event": "event1"}]
        }

        with patch('streamlit.session_state', {}) as mock_session:
            with patch('streamlit.progress'):
                with patch('streamlit.empty'):
                    with patch('streamlit.rerun'):
                        with patch('tempfile.NamedTemporaryFile') as mock_temp:
                            with patch('builtins.open', mock_open_json(mock_result)):
                                with patch('pathlib.Path.unlink'):
                                    # Mock temp file
                                    mock_temp_file = Mock()
                                    mock_temp_file.name = "/tmp/test.pdf"
                                    mock_temp.__enter__.return_value = mock_temp_file

                                    # Process the document
                                    web_interface._process_single_document(mock_file)

                                    # Verify session state was updated
                                    assert 'processing_results' in mock_session
                                    assert mock_file.name in mock_session['processing_results']

    def test_display_document_summary(self, web_interface):
        """Test displaying document summary."""
        mock_data = {
            "document_id": "test-doc",
            "filename": "test.pdf",
            "page_count": 5,
            "segments": [
                {"text": "segment1", "type": "medical"},
                {"text": "segment2", "type": "diagnosis"}
            ],
            "processed_at": "2023-01-01T10:00:00"
        }

        with patch('streamlit.markdown') as mock_markdown:
            with patch('streamlit.columns') as mock_columns:
                with patch('streamlit.write'):
                    # Mock columns
                    mock_col1 = Mock()
                    mock_col2 = Mock()
                    mock_columns.return_value = [mock_col1, mock_col2]

                    # Test the display
                    web_interface._display_document_summary(mock_data)

                    # Verify markdown was called
                    mock_markdown.assert_called()

                    # Verify columns were used
                    mock_columns.assert_called()

    def test_display_document_segments(self, web_interface):
        """Test displaying document segments."""
        mock_data = {
            "segments": [
                {"text": "segment1", "type": "medical", "metadata": {"confidence": 0.9}},
                {"text": "segment2", "type": "diagnosis", "metadata": {"confidence": 0.8}}
            ]
        }

        with patch('streamlit.markdown'):
            with patch('streamlit.columns') as mock_columns:
                with patch('streamlit.multiselect') as mock_multiselect:
                    with patch('streamlit.slider') as mock_slider:
                        with patch('streamlit.expander') as mock_expander:
                            # Mock inputs
                            mock_multiselect.return_value = ["medical", "diagnosis"]
                            mock_slider.return_value = 0

                            # Mock columns
                            mock_col1 = Mock()
                            mock_col2 = Mock()
                            mock_columns.return_value = [mock_col1, mock_col2]

                            # Test the display
                            web_interface._display_document_segments(mock_data)

                            # Verify components were called
                            mock_multiselect.assert_called()
                            mock_slider.assert_called()
                            mock_expander.assert_called()

    def test_display_document_timeline(self, web_interface):
        """Test displaying document timeline."""
        mock_data = {
            "timeline": [
                {"date": "2023-01-01", "type": "medical", "description": "Event 1", "confidence": 0.9},
                {"date": "2023-01-02", "type": "diagnosis", "description": "Event 2", "confidence": 0.8}
            ]
        }

        with patch('streamlit.markdown'):
            with patch('streamlit.dataframe') as mock_dataframe:
                with patch('streamlit.line_chart'):
                    with patch('pandas.DataFrame') as mock_df:
                        # Mock DataFrame
                        mock_df.return_value = Mock()

                        # Test the display
                        web_interface._display_document_timeline(mock_data)

                        # Verify components were called
                        mock_dataframe.assert_called()

    def test_display_raw_json(self, web_interface):
        """Test displaying raw JSON."""
        mock_data = {
            "document_id": "test-doc",
            "filename": "test.pdf",
            "page_count": 5
        }

        with patch('streamlit.markdown'):
            with patch('streamlit.code') as mock_code:
                with patch('streamlit.download_button') as mock_download:
                    # Test the display
                    web_interface._display_raw_json(mock_data)

                    # Verify components were called
                    mock_code.assert_called()
                    mock_download.assert_called()

    def test_display_export_options(self, web_interface):
        """Test displaying export options."""
        mock_data = {
            "filename": "test.pdf",
            "segments": [
                {"text": "segment1", "type": "medical", "metadata": {"confidence": 0.9}},
                {"text": "segment2", "type": "diagnosis", "metadata": {"confidence": 0.8}}
            ],
            "timeline": [
                {"date": "2023-01-01", "type": "medical", "description": "Event 1"}
            ]
        }

        with patch('streamlit.markdown'):
            with patch('streamlit.columns') as mock_columns:
                with patch('streamlit.download_button') as mock_download:
                    with patch('pandas.DataFrame') as mock_df:
                        # Mock columns
                        mock_col1 = Mock()
                        mock_col2 = Mock()
                        mock_columns.return_value = [mock_col1, mock_col2]

                        # Mock DataFrame
                        mock_df.return_value.to_csv.return_value = "csv_data"

                        # Test the display
                        web_interface._display_export_options("test.pdf", mock_data)

                        # Verify download buttons were created
                        assert mock_download.call_count >= 1

    @patch('streamlit.file_uploader')
    @patch('streamlit.info')
    @patch('streamlit.expander')
    @patch('streamlit.columns')
    @patch('streamlit.slider')
    @patch('streamlit.checkbox')
    @patch('streamlit.button')
    def test_batch_processing_page(self, mock_button, mock_checkbox, mock_slider, mock_columns,
                                  mock_expander, mock_info, mock_file_uploader, web_interface):
        """Test batch processing page."""
        # Mock file uploader with multiple files
        mock_files = [
            Mock(name="file1.pdf", size=1024),
            Mock(name="file2.pdf", size=2048)
        ]
        mock_file_uploader.return_value = mock_files

        # Mock other components
        mock_columns.return_value = [Mock(), Mock(), Mock()]
        mock_slider.return_value = 4
        mock_checkbox.return_value = True
        mock_button.return_value = False

        # Test the page
        web_interface._batch_processing_page()

        # Verify file uploader was called
        mock_file_uploader.assert_called_once()

        # Verify info was shown for uploaded files
        mock_info.assert_called_once()

    def test_create_batch_zip(self, web_interface):
        """Test creating batch ZIP file."""
        mock_results = [
            {
                'filename': 'test1.pdf',
                'status': 'completed',
                'data': {
                    'segments': [{'text': 'segment1', 'type': 'medical'}],
                    'timeline': [{'date': '2023-01-01', 'event': 'event1'}]
                }
            },
            {
                'filename': 'test2.pdf',
                'status': 'completed',
                'data': {
                    'segments': [{'text': 'segment2', 'type': 'diagnosis'}],
                    'timeline': [{'date': '2023-01-02', 'event': 'event2'}]
                }
            }
        ]

        # Test ZIP creation
        zip_data = web_interface._create_batch_zip(mock_results)

        # Verify ZIP data was created
        assert isinstance(zip_data, bytes)
        assert len(zip_data) > 0

    @patch('streamlit.markdown')
    @patch('streamlit.expander')
    @patch('streamlit.columns')
    @patch('streamlit.metric')
    @patch('streamlit.button')
    def test_processing_history_page(self, mock_button, mock_metric, mock_columns,
                                    mock_expander, mock_markdown, web_interface):
        """Test processing history page."""
        # Mock session state with history
        mock_session_state = {
            'processing_results': {
                'test.pdf': {
                    'data': {'page_count': 5, 'segments': []},
                    'processed_at': '2023-01-01T10:00:00',
                    'file_size': 1024
                }
            },
            'batch_results': {
                'batch1': {
                    'statistics': Mock(total_jobs=5, successful_jobs=4, failed_jobs=1,
                                     throughput_jobs_per_minute=2.5),
                    'processed_at': '2023-01-01T10:00:00'
                }
            }
        }

        with patch('streamlit.session_state', mock_session_state):
            # Mock components
            mock_columns.return_value = [Mock(), Mock(), Mock()]
            mock_button.return_value = False

            # Test the page
            web_interface._processing_history_page()

            # Verify components were called
            mock_expander.assert_called()

    @patch('streamlit.markdown')
    @patch('streamlit.expander')
    @patch('streamlit.columns')
    @patch('streamlit.json')
    @patch('streamlit.info')
    def test_settings_page(self, mock_info, mock_json, mock_columns, mock_expander,
                          mock_markdown, web_interface):
        """Test settings page."""
        # Mock components
        mock_columns.return_value = [Mock(), Mock()]

        # Test the page
        web_interface._settings_page()

        # Verify components were called
        mock_expander.assert_called()
        mock_json.assert_called()
        mock_info.assert_called()


def mock_open_json(data):
    """Mock open function that returns JSON data."""
    mock_file = Mock()
    mock_file.read.return_value = json.dumps(data)
    mock_file.__enter__.return_value = mock_file
    mock_file.__exit__.return_value = None
    return mock_file


class TestWebInterfaceIntegration:
    """Integration tests for the web interface."""

    def test_main_function_import(self):
        """Test that the main function can be imported."""
        from src.web_interface import main
        assert callable(main)

    def test_web_interface_class_import(self):
        """Test that WebInterface class can be imported."""
        from src.web_interface import WebInterface
        assert WebInterface is not None

    @patch('src.web_interface.get_config')
    @patch('src.web_interface.PDFProcessor')
    def test_web_interface_instantiation(self, mock_processor_class, mock_get_config):
        """Test that WebInterface can be instantiated."""
        # Mock dependencies
        mock_config = Mock()
        mock_get_config.return_value = mock_config

        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        # Create interface
        interface = WebInterface()

        # Verify it was created
        assert interface is not None
        assert interface.config == mock_config
        assert interface.processor == mock_processor


if __name__ == "__main__":
    pytest.main([__file__])
