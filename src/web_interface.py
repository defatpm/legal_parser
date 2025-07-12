"""Streamlit web interface for the medical record processor."""

import io
import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from .batch_processor import BatchProcessor, BatchProgress
from .models.document import DocumentSegment
from .process_pdf import PDFProcessor
from .utils.config import get_config
from .utils.output_formatter import to_csv_string, to_excel


class WebInterface:
    """Main web interface controller."""

    def __init__(self):
        """Initialize the web interface."""
        self.config = get_config()
        self.processor = PDFProcessor()

        # Initialize session state
        if "processing_results" not in st.session_state:
            st.session_state.processing_results = {}
        if "batch_results" not in st.session_state:
            st.session_state.batch_results = {}
        if "processing_status" not in st.session_state:
            st.session_state.processing_status = {}

    def run(self):
        """Main application entry point."""
        st.set_page_config(
            page_title="Medical Record Processor",
            page_icon="📄",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        # Custom CSS for better styling
        st.markdown(
            """
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1e3a8a;
            text-align: center;
            margin-bottom: 2rem;
        }
        .section-header {
            font-size: 1.5rem;
            color: #3b82f6;
            margin: 1rem 0;
        }
        .status-success {
            background-color: #d1fae5;
            border: 1px solid #10b981;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        .status-error {
            background-color: #fee2e2;
            border: 1px solid #ef4444;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        .status-processing {
            background-color: #fef3c7;
            border: 1px solid #f59e0b;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        .json-container {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 0.5rem;
            padding: 1rem;
            font-family: monospace;
            max-height: 400px;
            overflow-y: auto;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        # Main header
        st.markdown(
            '<h1 class="main-header">📄 Medical Record Processor</h1>',
            unsafe_allow_html=True,
        )

        # Sidebar navigation
        st.sidebar.title("Navigation")
        page = st.sidebar.selectbox(
            "Choose a page",
            ["Single Document", "Batch Processing", "Processing History", "Settings"],
        )

        # Route to appropriate page
        if page == "Single Document":
            self._single_document_page()
        elif page == "Batch Processing":
            self._batch_processing_page()
        elif page == "Processing History":
            self._processing_history_page()
        elif page == "Settings":
            self._settings_page()

    def _single_document_page(self):
        """Single document processing page."""
        st.markdown(
            '<h2 class="section-header">Single Document Processing</h2>',
            unsafe_allow_html=True,
        )

        # File upload
        uploaded_file = st.file_uploader(
            "Upload a PDF file", type=["pdf"], help="Select a PDF file to process"
        )

        if uploaded_file is not None:
            # Display file info
            st.info(f"📄 **File:** {uploaded_file.name} ({uploaded_file.size:,} bytes)")

            # Processing options
            col1, col2 = st.columns(2)

            with col1:
                process_button = st.button("🚀 Process Document", type="primary")

            with col2:
                if st.button("🔄 Clear Results"):
                    if uploaded_file.name in st.session_state.processing_results:
                        del st.session_state.processing_results[uploaded_file.name]
                    st.rerun()

            # Process the document
            if process_button:
                self._process_single_document(uploaded_file)

            # Show results if available
            if uploaded_file.name in st.session_state.processing_results:
                self._display_single_document_results(uploaded_file.name)

    def _process_single_document(self, uploaded_file: UploadedFile):
        """Process a single uploaded document."""
        file_key = uploaded_file.name

        # Update status
        st.session_state.processing_status[file_key] = "processing"

        # Create progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # Save uploaded file to temp directory
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = Path(tmp_file.name)

            # Process through the pipeline
            status_text.text("📄 Extracting text from PDF...")
            progress_bar.progress(20)

            # Create output path
            output_path = tmp_path.parent / f"{tmp_path.stem}_processed.json"

            # Process the document
            status_text.text("🔍 Analyzing document structure...")
            progress_bar.progress(40)

            status_text.text("📊 Extracting metadata...")
            progress_bar.progress(60)

            status_text.text("📅 Building timeline...")
            progress_bar.progress(80)

            # Actually process the document
            result_path = self.processor.process_pdf(tmp_path, output_path)

            # Load results
            with open(result_path, encoding="utf-8") as f:
                result_data = json.load(f)

            # Store results
            st.session_state.processing_results[file_key] = {
                "data": result_data,
                "processed_at": datetime.now().isoformat(),
                "file_size": uploaded_file.size,
                "processing_time": 0.0,  # Would need actual timing
            }

            status_text.text("✅ Processing completed successfully!")
            progress_bar.progress(100)

            # Update status
            st.session_state.processing_status[file_key] = "completed"

            # Clean up temp files
            tmp_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)

            # Auto-refresh to show results
            st.rerun()

        except Exception as e:
            st.session_state.processing_status[file_key] = "error"
            st.error(f"❌ Processing failed: {str(e)}")
            progress_bar.empty()
            status_text.empty()

    def _display_single_document_results(self, file_key: str):
        """Display results for a single document."""
        if file_key not in st.session_state.processing_results:
            return

        result = st.session_state.processing_results[file_key]
        data = result["data"]

        st.markdown(
            '<h3 class="section-header">📊 Processing Results</h3>',
            unsafe_allow_html=True,
        )

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("📄 Pages", data.get("page_count", 0))

        with col2:
            st.metric("📝 Segments", len(data.get("segments", [])))

        with col3:
            st.metric("📅 Timeline Events", len(data.get("timeline", [])))

        with col4:
            st.metric("📁 File Size", f"{result['file_size']:,} bytes")

        # Tabbed results view
        tabs = st.tabs(
            ["📋 Summary", "📝 Segments", "📅 Timeline", "📄 Raw JSON", "💾 Export"]
        )

        with tabs[0]:  # Summary
            self._display_document_summary(data)

        with tabs[1]:  # Segments
            self._display_document_segments(data)

        with tabs[2]:  # Timeline
            self._display_document_timeline(data)

        with tabs[3]:  # Raw JSON
            self._display_raw_json(data)

        with tabs[4]:  # Export
            self._display_export_options(file_key, data)

    def _display_document_summary(self, data: dict[str, Any]):
        """Display document summary."""
        st.markdown("### Document Overview")

        # Basic info
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Document ID:**", data.get("document_id", "N/A"))
            st.write("**Filename:**", data.get("filename", "N/A"))
            st.write("**Pages:**", data.get("page_count", 0))

        with col2:
            processed_at = data.get("processed_at")
            if processed_at:
                st.write("**Processed At:**", processed_at)

            # Processing stats
            segments = data.get("segments", [])
            if segments:
                segment_types = {}
                for segment in segments:
                    seg_type = segment.get("type", "unknown")
                    segment_types[seg_type] = segment_types.get(seg_type, 0) + 1

                st.write("**Segment Types:**")
                for seg_type, count in segment_types.items():
                    st.write(f"  - {seg_type}: {count}")

    def _display_document_segments(self, data: dict[str, Any]):
        """Display document segments."""
        segments = data.get("segments", [])

        if not segments:
            st.info("No segments found in the document.")
            return

        st.markdown(f"### Document Segments ({len(segments)} total)")

        # Filter controls
        col1, col2 = st.columns(2)

        with col1:
            segment_types = {seg.get("type", "unknown") for seg in segments}
            selected_types = st.multiselect(
                "Filter by type", sorted(segment_types), default=sorted(segment_types)
            )

        with col2:
            min_length = st.slider("Minimum text length", 0, 1000, 0)

        # Filter segments
        filtered_segments = []
        for segment in segments:
            if segment.get("type", "unknown") in selected_types:
                if len(segment.get("text", "")) >= min_length:
                    filtered_segments.append(segment)

        # Display segments
        for i, segment in enumerate(filtered_segments):
            with st.expander(
                f"Segment {i + 1}: {segment.get('type', 'unknown')} ({len(segment.get('text', ''))} chars)"
            ):
                st.write("**Type:**", segment.get("type", "unknown"))
                st.write("**Text:**")
                st.text_area(
                    "", segment.get("text", ""), height=100, key=f"segment_{i}"
                )

                # Metadata
                metadata = segment.get("metadata", {})
                if metadata:
                    st.write("**Metadata:**")
                    st.json(metadata)

    def _display_document_timeline(self, data: dict[str, Any]):
        """Display document timeline."""
        timeline = data.get("timeline", [])

        if not timeline:
            st.info("No timeline events found in the document.")
            return

        st.markdown(f"### Document Timeline ({len(timeline)} events)")

        # Create timeline DataFrame
        timeline_data = []
        for event in timeline:
            timeline_data.append(
                {
                    "Date": event.get("date", "Unknown"),
                    "Type": event.get("type", "Unknown"),
                    "Description": event.get("description", "")[:100]
                    + ("..." if len(event.get("description", "")) > 100 else ""),
                    "Confidence": event.get("confidence", 0),
                }
            )

        if timeline_data:
            df = pd.DataFrame(timeline_data)
            st.dataframe(df, use_container_width=True)

            # Timeline chart
            if len(timeline_data) > 1:
                st.markdown("### Timeline Visualization")
                # Create a simple timeline chart
                chart_data = pd.DataFrame(timeline_data)
                if "Date" in chart_data.columns:
                    try:
                        chart_data["Date"] = pd.to_datetime(
                            chart_data["Date"], errors="coerce"
                        )
                        chart_data = chart_data.dropna(subset=["Date"])
                        if not chart_data.empty:
                            st.line_chart(chart_data.set_index("Date")["Confidence"])
                    except (ValueError, TypeError):
                        st.info("Unable to create timeline chart - date format issues")

    def _display_raw_json(self, data: dict[str, Any]):
        """Display raw JSON data."""
        st.markdown("### Raw JSON Output")

        # Format JSON nicely
        json_str = json.dumps(data, indent=2, ensure_ascii=False)

        # Display in expandable code block
        st.code(json_str, language="json")

        # Download button
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"{data.get('filename', 'document')}_processed.json",
            mime="application/json",
        )

    def _display_export_options(self, file_key: str, data: dict[str, Any]):
        """Display export options."""
        st.markdown("### Export Options")

        col1, col2, col3 = st.columns(3)

        with col1:
            # JSON export
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"{data.get('filename', 'document')}_processed.json",
                mime="application/json",
            )

        with col2:
            # CSV export for segments
            segments_data = data.get("segments", [])
            if segments_data:
                segments = [DocumentSegment(**s) for s in segments_data]
                csv_str = to_csv_string(segments)

                st.download_button(
                    label="📊 Download Segments CSV",
                    data=csv_str,
                    file_name=f"{data.get('filename', 'document')}_segments.csv",
                    mime="text/csv",
                )

        with col3:
            # Excel export for segments
            segments_data = data.get("segments", [])
            if segments_data:
                segments = [DocumentSegment(**s) for s in segments_data]
                excel_data = to_excel(segments)

                st.download_button(
                    label="📄 Download Segments Excel",
                    data=excel_data,
                    file_name=f"{data.get('filename', 'document')}_segments.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        # Timeline export
        timeline = data.get("timeline", [])
        if timeline:
            st.markdown("### Timeline Export")

            timeline_df = pd.DataFrame(timeline)
            timeline_csv = timeline_df.to_csv(index=False)

            st.download_button(
                label="📅 Download Timeline CSV",
                data=timeline_csv,
                file_name=f"{data.get('filename', 'document')}_timeline.csv",
                mime="text/csv",
            )

    def _batch_processing_page(self):
        """Batch processing page."""
        st.markdown(
            '<h2 class="section-header">Batch Processing</h2>', unsafe_allow_html=True
        )

        # File upload (multiple files)
        uploaded_files = st.file_uploader(
            "Upload multiple PDF files",
            type=["pdf"],
            accept_multiple_files=True,
            help="Select multiple PDF files to process in batch",
        )

        if uploaded_files:
            st.info(f"📄 **Files selected:** {len(uploaded_files)} files")

            # Display file list
            with st.expander("📋 View selected files"):
                for i, file in enumerate(uploaded_files):
                    st.write(f"{i + 1}. {file.name} ({file.size:,} bytes)")

            # Processing options
            col1, col2, col3 = st.columns(3)

            with col1:
                max_workers = st.slider("👥 Concurrent workers", 1, 8, 4)

            with col2:
                show_progress = st.checkbox("📊 Show progress", value=True)

            with col3:
                process_button = st.button("🚀 Process Batch", type="primary")

            # Process batch
            if process_button:
                self._process_batch(uploaded_files, max_workers, show_progress)

            # Show batch results if available
            batch_key = f"batch_{len(uploaded_files)}_{hash(tuple(f.name for f in uploaded_files))}"
            if batch_key in st.session_state.batch_results:
                self._display_batch_results(batch_key)

    def _process_batch(
        self, uploaded_files: list[UploadedFile], max_workers: int, show_progress: bool
    ):
        """Process multiple files in batch."""
        batch_key = (
            f"batch_{len(uploaded_files)}_{hash(tuple(f.name for f in uploaded_files))}"
        )

        # Initialize progress tracking
        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()
            metrics_container = st.container()

        try:
            # Create temporary directory for batch processing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                input_dir = temp_path / "input"
                output_dir = temp_path / "output"
                input_dir.mkdir()
                output_dir.mkdir()

                # Save uploaded files
                file_paths = []
                for uploaded_file in uploaded_files:
                    file_path = input_dir / uploaded_file.name
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.read())
                    file_paths.append(file_path)

                # Create batch processor
                def progress_callback(progress: BatchProgress):
                    if show_progress:
                        percentage = progress.completion_rate
                        progress_bar.progress(percentage / 100)

                        status_text.text(
                            f"Processing: {progress.completed_jobs}/{progress.total_jobs} completed"
                        )

                        # Update metrics
                        with metrics_container:
                            col1, col2, col3, col4 = st.columns(4)

                            with col1:
                                st.metric("✅ Completed", progress.completed_jobs)

                            with col2:
                                st.metric("❌ Failed", progress.failed_jobs)

                            with col3:
                                st.metric("⏳ Processing", progress.processing_jobs)

                            with col4:
                                eta = progress.eta_seconds
                                eta_str = (
                                    f"{int(eta // 60)}:{int(eta % 60):02d}"
                                    if eta
                                    else "N/A"
                                )
                                st.metric("⏱️ ETA", eta_str)

                batch_processor = BatchProcessor(
                    max_workers=max_workers,
                    progress_callback=progress_callback if show_progress else None,
                )

                # Add files to batch
                for file_path in file_paths:
                    output_path = output_dir / f"{file_path.stem}.json"
                    batch_processor.add_file(file_path, output_path)

                # Process batch
                statistics = batch_processor.process_batch()

                # Collect results
                results = []
                for job in batch_processor.jobs:
                    if job.status == "completed" and job.result:
                        # Load the JSON result
                        try:
                            with open(job.output_path, encoding="utf-8") as f:
                                result_data = json.load(f)

                            results.append(
                                {
                                    "filename": job.input_path.name,
                                    "status": job.status,
                                    "data": result_data,
                                    "duration": job.duration,
                                    "result": job.result,
                                }
                            )
                        except Exception as e:
                            results.append(
                                {
                                    "filename": job.input_path.name,
                                    "status": "error",
                                    "error": str(e),
                                    "duration": job.duration,
                                }
                            )
                    else:
                        results.append(
                            {
                                "filename": job.input_path.name,
                                "status": job.status,
                                "error": job.error,
                                "duration": job.duration,
                            }
                        )

                # Store batch results
                st.session_state.batch_results[batch_key] = {
                    "statistics": statistics,
                    "results": results,
                    "processed_at": datetime.now().isoformat(),
                }

                if show_progress:
                    status_text.text("✅ Batch processing completed!")
                    progress_bar.progress(100)

                st.success(
                    f"✅ Batch processing completed! {statistics.successful_jobs} successful, {statistics.failed_jobs} failed"
                )

                # Auto-refresh to show results
                st.rerun()

        except Exception as e:
            st.error(f"❌ Batch processing failed: {str(e)}")

    def _display_batch_results(self, batch_key: str):
        """Display batch processing results."""
        if batch_key not in st.session_state.batch_results:
            return

        batch_result = st.session_state.batch_results[batch_key]
        statistics = batch_result["statistics"]
        results = batch_result["results"]

        st.markdown(
            '<h3 class="section-header">📊 Batch Processing Results</h3>',
            unsafe_allow_html=True,
        )

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("📄 Total Files", statistics.total_jobs)

        with col2:
            st.metric("✅ Successful", statistics.successful_jobs)

        with col3:
            st.metric("❌ Failed", statistics.failed_jobs)

        with col4:
            st.metric(
                "⚡ Throughput",
                f"{statistics.throughput_jobs_per_minute:.1f} files/min",
            )

        # Performance metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("⏱️ Average Duration", f"{statistics.average_duration:.2f}s")

        with col2:
            st.metric("🏃 Fastest", f"{statistics.fastest_job:.2f}s")

        with col3:
            st.metric("🐌 Slowest", f"{statistics.slowest_job:.2f}s")

        # Results table
        st.markdown("### 📋 Processing Results")

        # Create results DataFrame
        results_data = []
        for result in results:
            results_data.append(
                {
                    "Filename": result["filename"],
                    "Status": result["status"],
                    "Duration (s)": result.get("duration", 0),
                    "Pages": (
                        result.get("result", {}).get("pages", 0)
                        if result.get("result")
                        else 0
                    ),
                    "Segments": (
                        result.get("result", {}).get("segments", 0)
                        if result.get("result")
                        else 0
                    ),
                    "Error": result.get("error", ""),
                }
            )

        df = pd.DataFrame(results_data)
        st.dataframe(df, use_container_width=True)

        # Export options
        st.markdown("### 💾 Export Batch Results")

        col1, col2 = st.columns(2)

        with col1:
            # Export summary CSV
            summary_csv = df.to_csv(index=False)
            st.download_button(
                label="📊 Download Summary CSV",
                data=summary_csv,
                file_name=f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

        with col2:
            # Export all results as ZIP
            if st.button("📦 Download All Results (ZIP)"):
                zip_data = self._create_batch_zip(results)
                st.download_button(
                    label="📥 Download ZIP",
                    data=zip_data,
                    file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                )

    def _create_batch_zip(self, results: list[dict]) -> bytes:
        """Create a ZIP file with all batch results."""
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for result in results:
                if result["status"] == "completed" and "data" in result:
                    filename = result["filename"]
                    json_data = json.dumps(result["data"], indent=2, ensure_ascii=False)

                    # Add JSON file
                    zip_file.writestr(f"{filename}.json", json_data)

                    # Add segments CSV if available
                    segments_data = result["data"].get("segments", [])
                    if segments_data:
                        segments = [DocumentSegment(**s) for s in segments_data]
                        csv_str = to_csv_string(segments)
                        zip_file.writestr(
                            f"{Path(filename).stem}_segments.csv", csv_str
                        )

                    # Add segments Excel if available
                    segments_data = result["data"].get("segments", [])
                    if segments_data:
                        segments = [DocumentSegment(**s) for s in segments_data]
                        excel_data = to_excel(segments)
                        zip_file.writestr(
                            f"{Path(filename).stem}_segments.xlsx", excel_data
                        )

        zip_buffer.seek(0)
        return zip_buffer.read()

    def _processing_history_page(self):
        """Processing history page."""
        st.markdown(
            '<h2 class="section-header">Processing History</h2>', unsafe_allow_html=True
        )

        # Single document history
        if st.session_state.processing_results:
            st.markdown("### 📄 Single Document History")

            for file_key, result in list(st.session_state.processing_results.items()):
                with st.expander(f"📄 {file_key} - {result['processed_at'][:19]}"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("📄 Pages", result["data"].get("page_count", 0))

                    with col2:
                        st.metric(
                            "📝 Segments", len(result["data"].get("segments", []))
                        )

                    with col3:
                        st.metric("📁 Size", f"{result['file_size']:,} bytes")

                    if st.button(
                        f"🔄 Reprocess {file_key}", key=f"reprocess_{file_key}"
                    ):
                        # Remove from results to allow reprocessing
                        del st.session_state.processing_results[file_key]
                        st.rerun()

        # Batch processing history
        if st.session_state.batch_results:
            st.markdown("### 📦 Batch Processing History")

            for _batch_key, batch_result in st.session_state.batch_results.items():
                statistics = batch_result["statistics"]

                with st.expander(
                    f"📦 Batch - {batch_result['processed_at'][:19]} ({statistics.total_jobs} files)"
                ):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("📄 Total", statistics.total_jobs)

                    with col2:
                        st.metric("✅ Success", statistics.successful_jobs)

                    with col3:
                        st.metric("❌ Failed", statistics.failed_jobs)

                    with col4:
                        st.metric(
                            "⚡ Speed",
                            f"{statistics.throughput_jobs_per_minute:.1f}/min",
                        )

        # Clear history
        if st.session_state.processing_results or st.session_state.batch_results:
            st.markdown("### 🗑️ Clear History")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🗑️ Clear Single Document History"):
                    st.session_state.processing_results = {}
                    st.rerun()

            with col2:
                if st.button("🗑️ Clear Batch History"):
                    st.session_state.batch_results = {}
                    st.rerun()

    def _settings_page(self):
        """Settings and configuration page."""
        st.markdown('<h2 class="section-header">Settings</h2>', unsafe_allow_html=True)

        # Configuration display
        st.markdown("### ⚙️ Current Configuration")

        with st.expander("📋 View Configuration"):
            config_dict = {
                "app": {
                    "name": self.config.app.name,
                    "version": self.config.app.version,
                    "debug": self.config.app.debug,
                },
                "processing": {
                    "max_file_size_mb": self.config.processing.max_file_size_mb,
                    "timeout": {
                        "pdf_extraction": self.config.processing.timeout[
                            "pdf_extraction"
                        ],
                        "segmentation": self.config.processing.timeout["segmentation"],
                        "metadata_extraction": self.config.processing.timeout[
                            "metadata_extraction"
                        ],
                        "timeline_building": self.config.processing.timeout[
                            "timeline_building"
                        ],
                    },
                },
                "performance": {
                    "parallel": {
                        "enabled": self.config.performance.parallel["enabled"],
                        "workers": self.config.performance.parallel["workers"],
                        "chunk_size": self.config.performance.parallel["chunk_size"],
                    }
                },
            }

            st.json(config_dict)

        # System information
        st.markdown("### 💻 System Information")

        col1, col2 = st.columns(2)

        with col1:
            st.info(
                "🔧 **Processing Pipeline:**\n"
                "1. PDF Text Extraction\n"
                "2. Document Segmentation\n"
                "3. Metadata Extraction\n"
                "4. Timeline Building"
            )

        with col2:
            st.info(
                "📊 **Supported Formats:**\n"
                "- Input: PDF files\n"
                "- Output: JSON, CSV\n"
                "- Batch: Multiple files\n"
                "- Export: ZIP archives"
            )

        # Help and documentation
        st.markdown("### ❓ Help & Documentation")

        with st.expander("📖 How to Use"):
            st.markdown(
                """
            **Single Document Processing:**
            1. Go to the 'Single Document' page
            2. Upload a PDF file
            3. Click 'Process Document'
            4. View results in the tabs below

            **Batch Processing:**
            1. Go to the 'Batch Processing' page
            2. Upload multiple PDF files
            3. Configure processing options
            4. Click 'Process Batch'
            5. Download results as needed

            **Viewing Results:**
            - **Summary:** Overview of the document
            - **Segments:** Individual document sections
            - **Timeline:** Chronological events
            - **Raw JSON:** Complete processing output
            - **Export:** Download in various formats
            """
            )

        with st.expander("🔧 Troubleshooting"):
            st.markdown(
                """
            **Common Issues:**
            - **Large files:** Files over 100MB may take longer to process
            - **Scanned PDFs:** OCR processing may be slower
            - **Multiple files:** Use batch processing for better performance
            - **Memory issues:** Reduce concurrent workers if needed

            **Performance Tips:**
            - Use batch processing for multiple files
            - Adjust worker count based on system resources
            - Monitor processing progress
            - Clear history regularly to save memory
            """
            )


def main():
    """Main entry point for the web interface."""
    interface = WebInterface()
    interface.run()


if __name__ == "__main__":
    main()
