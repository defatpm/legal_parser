# Proposed Processor Refactoring: A Pipeline Approach

The current design separates processing logic into distinct classes (`PDFExtractor`, `DocumentSegmenter`, etc.), which is a robust and modular approach. Instead of consolidating all logic into a single `DocumentProcessor` class, we should introduce a `ProcessingPipeline` that orchestrates these components.

This pipeline approach maintains the excellent separation of concerns already present in the codebase while providing a simple, unified interface to execute the entire document processing workflow. It makes the system easier to test, maintain, and extend.

### Proposed `processing/pipeline.py`:

```python
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from .text_extractor import TextExtractor
from .segmenter import Segmenter
from .timeline_builder import TimelineBuilder
from ..core.document import Document

class ProcessingPipeline:
    """
    Orchestrates the entire document processing workflow by executing
    a series of modular processors.
    """
    def __init__(self, text_extractor: TextExtractor, segmenter: Segmenter, timeline_builder: TimelineBuilder):
        """
        Initializes the pipeline with specific processor implementations.

        Args:
            text_extractor: The component for extracting text from a document.
            segmenter: The component for segmenting the document text.
            timeline_builder: The component for building a timeline from the document.
        """
        self.text_extractor = text_extractor
        self.segmenter = segmenter
        self.timeline_builder = timeline_builder

    def run(self, input_path: Path) -> Document:
        """
        Executes the full processing pipeline on a given input file.

        Args:
            input_path: The path to the input PDF file.

        Returns:
            An enriched Document object with extracted text, segments, and a timeline.
        """
        print(f"Starting processing for: {input_path}")

        # 1. Extract text from the source file
        raw_text = self.text_extractor.extract(input_path)
        
        # 2. Segment the document into logical parts
        segments = self.segmenter.segment(raw_text)
        
        # 3. Build a timeline of events from the segments
        timeline_events = self.timeline_builder.build(segments)

        # 4. Assemble the final Document object
        processed_document = Document(
            source_path=str(input_path),
            content=raw_text,
            segments=segments,
            timeline=timeline_events,
            processed_at=datetime.now()
        )
        
        print("Processing complete.")
        return processed_document

    def to_json(self, document: Document, output_path: Path):
        """
        Serializes the processed document to a JSON file.
        """
        document.save_to_json(output_path)
        print(f"Output saved to: {output_path}")

```

### Rationale:

1.  **Dependency Injection:** The pipeline class receives its components (`TextExtractor`, `Segmenter`) via its constructor. This is a powerful pattern (Dependency Injection) that decouples the pipeline from specific implementations, making it highly configurable and testable.
2.  **Clear Workflow:** The `run` method explicitly defines the sequence of operations, making the processing logic easy to follow.
3.  **Maintains Modularity:** It leverages the existing processor classes, respecting the single-responsibility principle. Each class remains focused on its specific task.
4.  **Centralized Orchestration:** Provides a single entry point (`pipeline.run()`) for both the CLI and the web interface to use, eliminating code duplication.
5.  **Type Hinting:** Uses modern Python type hints for clarity and robustness.
