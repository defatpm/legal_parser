# Proposed Web UI Refactoring

The web interface should be a clean, user-facing layer that is fully decoupled from the backend processing logic. Its primary role is to handle user interactions and display data, not to manage the processing workflow itself.

This refactoring will align the web UI with the new `ProcessingPipeline`, resulting in a more modular, maintainable, and testable application.

### Key Principles:

1.  **Decoupling:** The Streamlit UI should not contain any business logic. It will delegate all processing tasks to the `ProcessingPipeline`.
2.  **Clear Entry Point:** The UI will be instantiated and run from a single, clear entry point: `src/legal_parser/web/app.py`.
3.  **State Management:** Use Streamlit's session state to manage UI-specific state, such as file uploads and results, without mixing it with processing state.

### Proposed `src/legal_parser/web/app.py`:

```python
import streamlit as st
from pathlib import Path
from tempfile import NamedTemporaryFile

# Import the pipeline and its components
from ..processing.pipeline import ProcessingPipeline
from ..processing.text_extractor import TextExtractor
from ..processing.segmenter import Segmenter
from ..processing.timeline_builder import TimelineBuilder
from ..core.document import Document

class WebUI:
    """
    A class to encapsulate the Streamlit web interface.
    """
    def __init__(self, pipeline: ProcessingPipeline):
        """
        Initializes the WebUI with a processing pipeline.
        """
        self.pipeline = pipeline
        st.set_page_config(page_title="Legal Document Analyzer", layout="wide")

    def run(self):
        """
        Runs the Streamlit application.
        """
        st.title("Legal Document Analyzer")

        uploaded_file = st.file_uploader(
            "Upload a legal PDF document", type="pdf"
        )

        if uploaded_file:
            self._handle_file_upload(uploaded_file)

    def _handle_file_upload(self, uploaded_file):
        """
        Handles the processing of a single uploaded file.
        """
        st.info(f"Processing `{uploaded_file.name}`...")

        # Use a temporary file to pass the path to the pipeline
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = Path(tmp.name)

        try:
            # 1. Delegate processing to the pipeline
            with st.spinner("Analyzing document... This may take a moment."):
                processed_document = self.pipeline.run(tmp_path)

            # 2. Display the results
            st.success("Processing complete!")
            self._display_results(processed_document)

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
        finally:
            # Clean up the temporary file
            tmp_path.unlink()

    def _display_results(self, document: Document):
        """
        Renders the processed document information in the UI.
        """
        st.header("Extracted Timeline")
        if not document.timeline:
            st.warning("No timeline events were extracted.")
        else:
            for event in document.timeline:
                st.write(f"- **{event.date}:** {event.description}")

        st.header("Document Segments")
        if not document.segments:
            st.warning("No segments were identified.")
        else:
            for i, segment in enumerate(document.segments):
                with st.expander(f"Segment {i+1}: {segment.type}"):
                    st.write(segment.content)

def main():
    """
    Application entry point.
    Initializes dependencies and runs the Web UI.
    """
    # 1. Initialize the processing components
    text_extractor = TextExtractor()
    segmenter = Segmenter()
    timeline_builder = TimelineBuilder()

    # 2. Assemble the pipeline
    pipeline = ProcessingPipeline(
        text_extractor=text_extractor,
        segmenter=segmenter,
        timeline_builder=timeline_builder
    )

    # 3. Initialize and run the UI
    ui = WebUI(pipeline)
    ui.run()

if __name__ == "__main__":
    main()
```

### How to Run It:

The application can be started with a simple command:

```bash
streamlit run src/legal_parser/web/app.py
```

This clean separation makes the system far more robust and easier to manage.
