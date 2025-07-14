import json
import time
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.interfaces.web.components.results import display_results
from src.utils.exceptions import PDFProcessingError


def single_document_page():
    """Render the single document processing page."""
    st.title("Single Document Processing")

    # File upload
    uploaded_file = st.file_uploader(
        "Upload PDF", type="pdf", help="Upload a medical record PDF (max 100MB)"
    )

    if uploaded_file:
        st.info(
            f"File: {uploaded_file.name} ({uploaded_file.size / 1024 / 1024:.2f} MB)"
        )

        if st.button("🚀 Process Document", type="primary"):
            with st.spinner("Processing document..."):
                progress = st.progress(0)
                status_text = st.empty()

                try:
                    # Save temp file
                    temp_path = Path(f"temp_{uploaded_file.name}")
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getvalue())

                    # Process
                    processor = st.session_state.processor
                    result_path = processor.process_pdf(temp_path)

                    # Update progress (simulated)
                    for i in range(1, 101):
                        progress.progress(i)
                        time.sleep(0.01)

                    # Load the result data from JSON file
                    with open(result_path) as f:
                        result_data = json.load(f)

                    # Save to history
                    doc_id = str(uuid.uuid4())
                    st.session_state.history[doc_id] = {
                        "filename": uploaded_file.name,
                        "timestamp": datetime.now().isoformat(),
                        "result": result_data,
                        "status": "completed",
                    }

                    status_text.success("Processing complete!")
                    display_results(result_data, uploaded_file.name)

                    # Clean up the temporary result file
                    result_path.unlink(missing_ok=True)

                except PDFProcessingError as e:
                    status_text.error(f"Error: {str(e)}")
                finally:
                    temp_path.unlink(missing_ok=True)
