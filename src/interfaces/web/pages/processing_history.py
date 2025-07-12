import streamlit as st

from src.interfaces.web.components.results import display_results


def processing_history_page():
    """Render the processing history page."""
    st.title("Processing History")

    if not st.session_state.history and not st.session_state.batch_history:
        st.info("No processing history yet.")
        return

    # Single document history
    st.subheader("Single Documents")
    for doc_id, item in st.session_state.history.items():
        with st.expander(f"{item['filename']} - {item['timestamp']}"):
            st.write(f"Status: {item['status']}")
            if st.button("🔄 Reprocess", key=f"reproc_{doc_id}"):
                # Reprocess logic
                pass
            display_results(item["result"], item["filename"])

    # Batch history
    st.subheader("Batch Operations")
    for batch_id, item in st.session_state.batch_history.items():
        with st.expander(f"Batch {len(item['filenames'])} files - {item['timestamp']}"):
            st.write(f"Status: {item['status']}")
            if st.button("🗑️ Clear", key=f"clear_{batch_id}"):
                del st.session_state.batch_history[batch_id]
                st.rerun()

    if st.button("🗑️ Clear All History"):
        st.session_state.history.clear()
        st.session_state.batch_history.clear()
        st.rerun()
