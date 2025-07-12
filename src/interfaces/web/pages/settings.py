import streamlit as st

from src.utils.config import ConfigManager


def settings_page():
    """Render the settings and configuration page."""
    st.title("Settings & Configuration")

    config = ConfigManager.get_instance()

    st.subheader("System Configuration")
    st.json(config.dict())

    st.subheader("System Information")
    st.write(f"Version: {config.app.version}")
    st.write("Processing Pipeline: PDF Extraction → Segmentation → Metadata → Timeline")
    st.write("Supported Formats: PDF")

    st.subheader("Help & Documentation")
    st.markdown(
        """
    - Upload PDFs in Single or Batch mode.
    - Monitor progress in real-time.
    - Export results as JSON, CSV, or ZIP.
    - For issues, check logs or restart the app.
    """
    )
