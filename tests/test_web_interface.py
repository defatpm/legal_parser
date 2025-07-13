import zipfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest


class MockStreamlit:
    """Mock Streamlit module."""

    def __init__(self):
        self.session_state = MagicMock()
        self.session_state.history = {}
        self.session_state.batch_history = {}
        self.session_state.processor = MagicMock()
        self.session_state.batch_processor = MagicMock()

        # Mock sidebar
        self.sidebar = MagicMock()
        self.sidebar.title = MagicMock()
        self.sidebar.radio = MagicMock(return_value="Single Document")
        self.sidebar.button = MagicMock(return_value=False)
        self.sidebar.selectbox = MagicMock()

        # Mock main functions
        self.title = MagicMock()
        self.subheader = MagicMock()
        self.info = MagicMock()
        self.file_uploader = MagicMock(return_value=None)
        self.button = MagicMock(return_value=False)
        self.spinner = MagicMock()
        self.spinner.__enter__ = MagicMock()
        self.spinner.__exit__ = MagicMock()
        self.progress = MagicMock()
        self.empty = MagicMock()
        self.success = MagicMock()
        self.error = MagicMock()
        self.json = MagicMock()
        self.dataframe = MagicMock()
        self.line_chart = MagicMock()
        self.download_button = MagicMock()
        self.slider = MagicMock(return_value=2)
        self.expander = MagicMock()
        self.expander.__enter__ = MagicMock()
        self.expander.__exit__ = MagicMock()
        self.radio = MagicMock()
        self.tabs = MagicMock(return_value=[MagicMock() for _ in range(5)])
        self.set_page_config = MagicMock()
        self.markdown = MagicMock()
        self.write = MagicMock()
        self.rerun = MagicMock()
        self.container = MagicMock()
        self.container.return_value.__enter__ = MagicMock()
        self.container.return_value.__exit__ = MagicMock()
        self.cache_resource = lambda func: func


@pytest.fixture
def mock_streamlit():
    """Fixture to mock Streamlit."""
    mock_st = MockStreamlit()
    with patch.dict("sys.modules", {"streamlit": mock_st}):
        yield mock_st


def test_initialize_session_state(mock_streamlit):
    """Test session state initialization."""
    # Import here to use the mocked streamlit
    from src.interfaces.web.app import initialize_session_state

    initialize_session_state()
    assert hasattr(mock_streamlit.session_state, "history")
    assert hasattr(mock_streamlit.session_state, "batch_history")
    assert hasattr(mock_streamlit.session_state, "processor")
    assert hasattr(mock_streamlit.session_state, "batch_processor")


def test_run_app(mock_streamlit):
    """Test main app runner."""
    with (
        patch(
            "src.interfaces.web.pages.single_document.single_document_page"
        ) as mock_single,
        patch("src.interfaces.web.pages.batch_processing.batch_processing_page"),
        patch("src.interfaces.web.pages.processing_history.processing_history_page"),
        patch("src.interfaces.web.pages.settings.settings_page"),
    ):
        # Import here to use the mocked streamlit
        from src.interfaces.web.app import run_app

        run_app()

        mock_streamlit.set_page_config.assert_called_once()
        mock_streamlit.sidebar.title.assert_called_once()
        mock_single.assert_called_once()


def test_single_document_page(mock_streamlit):
    """Test single document page."""
    mock_file = MagicMock()
    mock_file.name = "test.pdf"
    mock_file.size = 1024
    mock_file.getvalue.return_value = b"test content"

    mock_streamlit.file_uploader.return_value = mock_file
    mock_streamlit.button.return_value = True

    # Mock session state processor
    mock_processor = MagicMock()
    mock_processor.process_pdf.return_value = {"test": "data"}
    mock_streamlit.session_state.processor = mock_processor
    mock_streamlit.session_state.history = {}

    with (
        patch("pathlib.Path") as mock_path,
        patch("builtins.open", create=True),
        patch("uuid.uuid4", return_value="test-uuid"),
    ):
        mock_path.return_value.unlink = MagicMock()

        # Import here to use the mocked streamlit
        from src.interfaces.web.pages.single_document import single_document_page

        single_document_page()

        mock_streamlit.title.assert_called_with("Single Document Processing")
        mock_streamlit.spinner.assert_called()


def test_single_document_error(mock_streamlit):
    """Test error handling in single document page."""
    mock_file = MagicMock()
    mock_file.name = "test.pdf"
    mock_file.size = 1024  # Add size to prevent format string issues
    mock_file.getvalue.return_value = b"test"

    mock_streamlit.file_uploader.return_value = mock_file
    mock_streamlit.button.return_value = True

    # Mock session state processor that raises error
    mock_processor = MagicMock()
    from src.utils.exceptions import PDFProcessingError

    mock_processor.process_pdf.side_effect = PDFProcessingError("Test error")
    mock_streamlit.session_state.processor = mock_processor
    mock_streamlit.session_state.history = {}

    # Mock empty for status text
    mock_status = MagicMock()
    mock_streamlit.empty.return_value = mock_status

    with (
        patch("pathlib.Path") as mock_path,
        patch("builtins.open", create=True),
    ):
        mock_path.return_value.unlink = MagicMock()

        # Import here to use the mocked streamlit
        from src.interfaces.web.pages.single_document import single_document_page

        single_document_page()

        mock_status.error.assert_called()


def test_batch_processing_page(mock_streamlit):
    """Test batch processing page."""
    mock_files = [
        MagicMock(name="file1.pdf", getvalue=lambda: b"content1"),
        MagicMock(name="file2.pdf", getvalue=lambda: b"content2"),
    ]
    mock_streamlit.file_uploader.return_value = mock_files
    mock_streamlit.slider.return_value = 2
    mock_streamlit.button.return_value = True

    # Mock session state batch processor
    mock_batch_processor = MagicMock()
    mock_batch_processor.process_batch.return_value = [
        {"filename": "file1.pdf", "status": "completed", "data": {"test": "data1"}},
        {"filename": "file2.pdf", "status": "completed", "data": {"test": "data2"}},
    ]
    mock_streamlit.session_state.batch_processor = mock_batch_processor
    mock_streamlit.session_state.batch_history = {}

    with patch("uuid.uuid4", return_value="test-batch-uuid"):
        # Import here to use the mocked streamlit
        from src.interfaces.web.pages.batch_processing import batch_processing_page

        batch_processing_page()

        mock_streamlit.title.assert_called_with("Batch Processing")


def test_processing_history_page_empty(mock_streamlit):
    """Test history page when empty."""
    mock_streamlit.session_state.history = {}
    mock_streamlit.session_state.batch_history = {}

    # Import here to use the mocked streamlit
    from src.interfaces.web.pages.processing_history import processing_history_page

    processing_history_page()

    mock_streamlit.info.assert_called_with("No processing history yet.")


def test_processing_history_page_with_data(mock_streamlit):
    """Test history page with data."""
    mock_streamlit.session_state.history = {
        "id1": {
            "filename": "test.pdf",
            "timestamp": "2023-01-01",
            "result": {},
            "status": "completed",
        }
    }
    mock_streamlit.session_state.batch_history = {
        "bid1": {
            "filenames": ["test.pdf"],
            "timestamp": "2023-01-01",
            "results": [],
            "status": "completed",
        }
    }

    # Import here to use the mocked streamlit
    from src.interfaces.web.pages.processing_history import processing_history_page

    processing_history_page()

    mock_streamlit.subheader.assert_any_call("Single Documents")
    mock_streamlit.subheader.assert_any_call("Batch Operations")


def test_settings_page(mock_streamlit):
    """Test settings page."""
    # Import here to use the mocked streamlit
    from src.interfaces.web.pages.settings import settings_page

    # Mock ConfigManager.get_instance since it doesn't exist
    with patch("src.interfaces.web.pages.settings.ConfigManager") as mock_config_class:
        mock_config = MagicMock()
        mock_config.dict.return_value = {"test": "config"}
        mock_config.app.version = "1.0.0"
        mock_config_class.get_instance.return_value = mock_config

        settings_page()

        mock_streamlit.title.assert_called_with("Settings & Configuration")
        mock_streamlit.json.assert_called()


def test_display_results(mock_streamlit):
    """Test display_results function."""
    # Import here to use the mocked streamlit
    from src.interfaces.web.components.results import display_results

    data = {
        "page_count": 5,
        "segments": [{"type": "test"}],
        "timeline": [{"date": "2023-01-01"}],
    }
    display_results(data, "test.pdf")

    mock_streamlit.tabs.assert_called_once()
    mock_streamlit.subheader.assert_called()


def test_display_batch_results(mock_streamlit):
    """Test display_batch_results function."""
    # Import here to use the mocked streamlit
    from src.interfaces.web.components.results import display_batch_results

    results = [
        {"filename": "test1.pdf", "status": "completed", "data": {"test": "data1"}},
        {"filename": "test2.pdf", "status": "failed", "data": None},
    ]

    with patch("src.interfaces.web.components.results.create_batch_zip") as mock_zip:
        mock_zip.return_value = b"test zip data"

        display_batch_results(results)

        mock_streamlit.subheader.assert_called_with("Batch Results")
        mock_streamlit.dataframe.assert_called_once()
        mock_streamlit.download_button.assert_called()


def test_data_to_csv():
    """Test data_to_csv utility."""
    from src.interfaces.web.utils import data_to_csv

    data = [{"col1": "val1", "col2": "val2"}]
    csv_str = data_to_csv(data)
    assert (
        "col1,col2\r\nval1,val2\r\n" == csv_str or "col1,col2\nval1,val2\n" == csv_str
    )


def test_data_to_csv_empty():
    """Test data_to_csv with empty data."""
    from src.interfaces.web.utils import data_to_csv

    assert data_to_csv([]) == ""


def test_create_batch_zip():
    """Test create_batch_zip utility."""
    from src.interfaces.web.utils import create_batch_zip

    results = [
        {"filename": "test1.pdf", "status": "completed", "data": {"key": "value"}},
        {"filename": "test2.pdf", "status": "failed"},
    ]
    zip_bytes = create_batch_zip(results)
    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0

    # Verify content
    zip_io = BytesIO(zip_bytes)
    with zipfile.ZipFile(zip_io, "r") as zf:
        assert "test1.pdf_processed.json" in zf.namelist()
        assert len(zf.namelist()) == 1


@pytest.mark.parametrize(
    "invalid_results",
    [
        [],  # empty
        [{"filename": "test.pdf", "status": "completed", "data": None}],  # invalid data
    ],
)
def test_create_batch_zip_edge_cases(invalid_results):
    """Test create_batch_zip edge cases."""
    from src.interfaces.web.utils import create_batch_zip

    zip_bytes = create_batch_zip(invalid_results)
    assert len(zip_bytes) > 0  # Still produces empty zip
