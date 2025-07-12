CHANGELOG REGARDING REVISIONS FROM THE REFACTORING OF WEB_INTERFACE.PY:

•	Moved code to new directory: src/interfaces/web/ containing init.py, app.py (main app setup and navigation), pages/ (single_document.py, batch_processing.py, processing_history.py, settings.py), components/results.py (shared result displays), and utils.py (helpers like CSV/ZIP exports).

•	Updated run_web_interface.py to run src/interfaces/web/app.py via Streamlit.

•	Rewrote tests/test_web_interface.py with new imports (e.g., from src.interfaces.web.app import run_app) and fixtures/tests for modular components, pages, and utils; ensured coverage for key functions like session init, page rendering, error handling, and exports.

•	Import changes: Use relative imports within src/interfaces/web/; external imports (e.g., PDFProcessor) remain from src.process_pdf. Run pytest to verify.