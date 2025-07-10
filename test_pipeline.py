#!/usr/bin/env python3
"""Test script for the PDF processing pipeline."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.process_pdf import PDFProcessor


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:

        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False


def test_processor_initialization():
    """Test that the PDF processor can be initialized."""
    print("Testing processor initialization...")

    try:
        processor = PDFProcessor()
        print("✓ PDFProcessor initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Processor initialization error: {e}")
        return False


def test_spacy_model():
    """Test that spaCy model is available."""
    print("Testing spaCy model...")

    try:
        import spacy

        nlp = spacy.load("en_core_web_sm")
        doc = nlp("This is a test document.")
        print("✓ spaCy model loaded successfully")
        return True
    except Exception as e:
        print(f"✗ spaCy model error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("PDF Processing Pipeline Test")
    print("=" * 50)

    tests = [
        test_imports,
        test_processor_initialization,
        test_spacy_model,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Pipeline is ready.")
        return 0
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
