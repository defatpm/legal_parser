#!/usr/bin/env python3
"""Demo script to showcase the web interface functionality."""

from src.web_interface import WebInterface


def create_demo_pdf_content():
    """Create demo PDF content for testing."""
    return """
    MEDICAL RECORD

    Patient: John Doe
    Date: 2023-01-01

    HISTORY:
    Patient presents with chest pain and shortness of breath.

    EXAMINATION:
    Vital signs stable. Heart rate 72 bpm.

    DIAGNOSIS:
    Acute coronary syndrome suspected.

    TREATMENT:
    Prescribed aspirin 81mg daily.
    Follow-up in 2 weeks.

    Dr. Smith, MD
    Cardiology Department
    """


def demo_batch_processing():
    """Demonstrate batch processing functionality."""
    print("🎯 Web Interface Demo - Batch Processing")
    print("=" * 50)

    # Create web interface
    interface = WebInterface()

    # Create sample results for demo
    sample_results = [
        {
            "filename": "patient_001.pdf",
            "status": "completed",
            "data": {
                "document_id": "doc-001",
                "filename": "patient_001.pdf",
                "page_count": 3,
                "segments": [
                    {"text": "Patient presents with chest pain", "type": "history"},
                    {"text": "Vital signs stable", "type": "examination"},
                    {"text": "Acute coronary syndrome", "type": "diagnosis"},
                    {"text": "Prescribed aspirin", "type": "treatment"},
                ],
                "timeline": [
                    {
                        "date": "2023-01-01",
                        "type": "visit",
                        "description": "Initial consultation",
                    },
                    {
                        "date": "2023-01-15",
                        "type": "followup",
                        "description": "Follow-up appointment",
                    },
                ],
            },
        },
        {
            "filename": "patient_002.pdf",
            "status": "completed",
            "data": {
                "document_id": "doc-002",
                "filename": "patient_002.pdf",
                "page_count": 2,
                "segments": [
                    {"text": "Patient reports improvement", "type": "history"},
                    {"text": "Blood pressure normal", "type": "examination"},
                    {"text": "Continue current treatment", "type": "treatment"},
                ],
                "timeline": [
                    {
                        "date": "2023-01-15",
                        "type": "visit",
                        "description": "Follow-up visit",
                    }
                ],
            },
        },
        {
            "filename": "patient_003.pdf",
            "status": "failed",
            "error": "File corrupted",
            "duration": 5.2,
        },
    ]

    print(f"📄 Processing {len(sample_results)} documents...")
    print(
        f"✅ Successful: {sum(1 for r in sample_results if r['status'] == 'completed')}"
    )
    print(f"❌ Failed: {sum(1 for r in sample_results if r['status'] == 'failed')}")

    # Demonstrate ZIP creation
    print("\n📦 Creating batch export ZIP...")
    zip_data = interface._create_batch_zip(sample_results)
    print(f"✅ ZIP created: {len(zip_data):,} bytes")

    # Show export capabilities
    print("\n💾 Export Options Available:")
    print("  - JSON files for each document")
    print("  - CSV files for segments")
    print("  - Timeline CSV for chronological events")
    print("  - Summary CSV for batch overview")
    print("  - ZIP archive with all results")

    return sample_results


def demo_single_document():
    """Demonstrate single document processing."""
    print("\n🎯 Web Interface Demo - Single Document")
    print("=" * 50)

    # Create mock document data
    document_data = {
        "document_id": "demo-doc-001",
        "filename": "demo_medical_record.pdf",
        "page_count": 1,
        "processed_at": "2023-01-01T10:00:00Z",
        "segments": [
            {
                "text": "Patient presents with chest pain and shortness of breath.",
                "type": "history",
                "metadata": {"confidence": 0.95, "page": 1},
            },
            {
                "text": "Vital signs stable. Heart rate 72 bpm.",
                "type": "examination",
                "metadata": {"confidence": 0.92, "page": 1},
            },
            {
                "text": "Acute coronary syndrome suspected.",
                "type": "diagnosis",
                "metadata": {"confidence": 0.88, "page": 1},
            },
            {
                "text": "Prescribed aspirin 81mg daily. Follow-up in 2 weeks.",
                "type": "treatment",
                "metadata": {"confidence": 0.94, "page": 1},
            },
        ],
        "timeline": [
            {
                "date": "2023-01-01",
                "type": "visit",
                "description": "Initial consultation for chest pain",
                "confidence": 0.9,
            },
            {
                "date": "2023-01-15",
                "type": "followup",
                "description": "Scheduled follow-up appointment",
                "confidence": 0.8,
            },
        ],
    }

    print(f"📄 Document: {document_data['filename']}")
    print(f"📊 Pages: {document_data['page_count']}")
    print(f"📝 Segments: {len(document_data['segments'])}")
    print(f"📅 Timeline Events: {len(document_data['timeline'])}")

    # Show segment breakdown
    print("\n📋 Segment Breakdown:")
    segment_types = {}
    for segment in document_data["segments"]:
        seg_type = segment["type"]
        segment_types[seg_type] = segment_types.get(seg_type, 0) + 1

    for seg_type, count in segment_types.items():
        print(f"  - {seg_type}: {count}")

    # Show timeline
    print("\n📅 Timeline:")
    for event in document_data["timeline"]:
        print(f"  - {event['date']}: {event['description']}")

    # Show export options
    print("\n💾 Export Options:")
    print("  - Complete JSON with all data")
    print("  - CSV with segments")
    print("  - Timeline CSV")
    print("  - Individual component downloads")

    return document_data


def demo_interface_features():
    """Demonstrate key interface features."""
    print("\n🎯 Web Interface Features Overview")
    print("=" * 50)

    features = {
        "🖥️ User Interface": [
            "Intuitive Streamlit-based web interface",
            "Responsive design for desktop and mobile",
            "Custom CSS styling for professional appearance",
            "Multi-page navigation with sidebar",
        ],
        "📤 File Upload": [
            "Drag-and-drop file upload",
            "Multiple file selection for batch processing",
            "File size and type validation",
            "Upload progress indication",
        ],
        "⚡ Processing": [
            "Real-time progress tracking",
            "Concurrent batch processing",
            "Configurable worker threads",
            "ETA calculation and status updates",
        ],
        "📊 Results Display": [
            "Interactive tabbed interface",
            "Filterable and sortable data tables",
            "JSON syntax highlighting",
            "Timeline visualization charts",
        ],
        "💾 Export Options": [
            "JSON, CSV, and ZIP downloads",
            "Batch export with multiple formats",
            "Custom filename generation",
            "Structured data export",
        ],
        "📋 History Management": [
            "Session-based processing history",
            "Reprocessing capabilities",
            "Batch operation tracking",
            "History cleanup options",
        ],
    }

    for category, items in features.items():
        print(f"\n{category}:")
        for item in items:
            print(f"  ✅ {item}")

    print(
        f"\n🚀 Total Features Implemented: {sum(len(items) for items in features.values())}"
    )


def main():
    """Main demo function."""
    print("🎉 Medical Record Processor - Web Interface Demo")
    print("=" * 60)

    # Demo single document processing
    demo_single_document()

    # Demo batch processing
    demo_batch_processing()

    # Demo interface features
    demo_interface_features()

    print("\n🎯 How to Run the Web Interface:")
    print("=" * 40)
    print("1. Run: python run_web_interface.py")
    print("2. Open browser to: http://localhost:8501")
    print("3. Upload PDF files and start processing!")

    print("\n📖 Documentation:")
    print("- See WEB_INTERFACE_README.md for detailed usage guide")
    print("- Check PROGRESS.md for implementation details")
    print("- Review src/web_interface.py for technical details")

    print("\n✨ Demo completed successfully!")


if __name__ == "__main__":
    main()
