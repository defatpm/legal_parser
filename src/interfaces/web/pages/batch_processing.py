import uuid
from datetime import datetime

import streamlit as st

from src.interfaces.web.components.results import display_batch_results


def batch_processing_page():
    """Render the batch processing page."""
    st.title("Batch Processing")

    uploaded_files = st.file_uploader(
        "Upload PDFs",
        type="pdf",
        accept_multiple_files=True,
        help="Upload multiple medical record PDFs",
    )

    if uploaded_files:
        st.info(f"{len(uploaded_files)} files uploaded")

        workers = st.slider("Concurrent Workers", min_value=1, max_value=8, value=4)

        if st.button("🚀 Process Batch", type="primary"):
            with st.spinner("Processing batch..."):
                batch_processor = st.session_state.batch_processor
                results = batch_processor.process_batch(
                    uploaded_files, max_workers=workers
                )

                # Save to history
                batch_id = str(uuid.uuid4())
                st.session_state.batch_history[batch_id] = {
                    "filenames": [f.name for f in uploaded_files],
                    "timestamp": datetime.now().isoformat(),
                    "results": results,
                    "status": "completed",
                }

                display_batch_results(results)
