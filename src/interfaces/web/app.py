from typing import Any

import streamlit as st

from src.batch_processor import BatchProcessor
from src.process_pdf import PDFProcessor

# Load config
from src.utils.config import get_config

from .pages.batch_processing import batch_processing_page
from .pages.processing_history import processing_history_page
from .pages.settings import settings_page
from .pages.single_document import single_document_page

config = get_config()


@st.cache_resource
def get_processor():
    return PDFProcessor()


@st.cache_resource
def get_batch_processor():
    return BatchProcessor()


def initialize_session_state():
    if "history" not in st.session_state:
        st.session_state.history: dict[str, dict[str, Any]] = {}
    if "batch_history" not in st.session_state:
        st.session_state.batch_history: dict[str, dict[str, Any]] = {}
    if "processor" not in st.session_state:
        st.session_state.processor = get_processor()
    if "batch_processor" not in st.session_state:
        st.session_state.batch_processor = get_batch_processor()


def run_app():
    """Main entry point for the Streamlit app."""
    st.set_page_config(
        page_title=config.app.name,
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for styling
    st.markdown(
        """
        <style>
            .stApp { background-color: #f8f9fa; }
            .sidebar .sidebar-content { background-color: #ffffff; }
            .stButton > button { width: 100%; }
        </style>
    """,
        unsafe_allow_html=True,
    )

    initialize_session_state()

    # Sidebar navigation
    st.sidebar.title("Medical Record Processor")
    page = st.sidebar.radio(
        "Navigation",
        ["Single Document", "Batch Processing", "Processing History", "Settings"],
    )

    if page == "Single Document":
        single_document_page()
    elif page == "Batch Processing":
        batch_processing_page()
    elif page == "Processing History":
        processing_history_page()
    elif page == "Settings":
        settings_page()


if __name__ == "__main__":
    run_app()
