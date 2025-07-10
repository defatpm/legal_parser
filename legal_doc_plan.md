#LEGAL DOC CODING PLAN

##CONCEPT: THE INTELLIGENT MEDICAL RECORD PRE-PROCESSOR

The core problem isn't just splitting a large file. It's about transforming a single, monolithic document into a series of contextually-aware, analyzable, and chronologically-sorted data chunks. A simple 10-page split of a 1,300-page file is ineffective because it breaks in the middle of reports, separates lab results from the corresponding doctor's notes, and loses all sense of timeline.

Our goal should be to create a tool that acts as a "digital paralegal," organizing the file intelligently before it's ever seen by a summarization AI.


##PHASE 1: THE CORE PROCESSING ENGINE (BACKEND LOGIC)

This remains Python-based, as it's ideal for PDF handling and text analysis. Aim to build this as a standalone module first (e.g., a script that processes a file and outputs JSON), then expose it via an API in Phase 2.

###Step 1: File Ingestion and Text Extraction

Goal: Extract text reliably, handling both digital and scanned PDFs.
Technology: Use PyMuPDF (fitz) as primary for speed and positional data; fallback to pdfplumber for table-heavy pages. For OCR on low-text pages (e.g., <50 words detected), use pytesseract with Tesseract engine.

Enhancements: Process page-by-page to manage memory for large files. Extract images/tables as optional metadata if relevant (e.g., via pdfplumber's table extraction).
Output: A list of page objects, each with {page_number, raw_text, is_ocr_applied (bool)}.
Error Handling: Log failures (e.g., corrupted pages) and skip with warnings.

###Step 2: Document Segmentation and Noise Filtering

Goal: Identify logical boundaries and remove irrelevant content.

Logic: Concatenate all raw_text into a single string, then use regex to detect new record starts (e.g., r"Date of Service:\s*(\d{2}/\d{2}/\d{4})", r"^[A-Z ]{5,}$" for all-caps headers like "DISCHARGE SUMMARY"). Use positional data from PyMuPDF to detect headers/footers.

Noise Filtering Sub-Step: Flag/remove boilerplate via keyword matching (e.g., "fax cover sheet", "confidentiality notice") or similarity thresholds (e.g., using difflib to detect duplicates). Use spaCy (NLP library) for sentence-level analysis to filter non-narrative text like billing codes.

Output: A list of "raw segments," each with {text_content, page_start, page_end}.
Enhancements: If regex misses variations, add a basic ML fallback (e.g., spaCy's named entity recognition for dates/names as segment anchors).

###Step 3: Metadata Extraction per Segment

Goal: Enrich each segment with structured data.

Logic: For each segment, apply targeted regex/NLP:
Date of Service: Extract via regex (e.g., r"\d{2}/\d{2}/\d{4}") or spaCy's date entity recognition; validate and pick the most prominent (e.g., earliest in text).

Document Type: Infer from keywords (e.g., match against a predefined list: "ADMISSION NOTE" → "Admission").

Provider Name/Facility: Use spaCy for person/organization entities (e.g., "Dr. Smith" or "Mercy Hospital").

Additional Metadata: Add optional fields like patient_name (if consistent) and keywords (top terms via TF-IDF for quick searchability).
Output: A list of structured dicts, each: {text_content, date (datetime object), document_type, provider, page_start, page_end, keywords}.

###Step 4: Chronological Sorting, Intelligent Chunking, and Final Output

Goal: Create a timeline-ready structure with AI-friendly chunks.

Logic: Sort the list by date (handle missing dates by estimating from page order or flagging for manual review).

Intelligent Chunking Sub-Step: For segments exceeding a token limit (e.g., 4K tokens, estimable via len(text)/4), split by paragraphs/sections using NLTK or spaCy sentence tokenization. Each sub-chunk inherits parent metadata and adds {chunk_id, parent_segment_id}.

Output: A JSON file/object with {timeline: [sorted_segments]}, where each segment includes chunks if needed. Include a summary header (e.g., total_segments, date_range).


##PHASE 2: THE USER INTERFACE (FRONTEND APPLICATION)

Build a web app for easy interaction. Use Flask (Python) for the backend API to run the Phase 1 engine; frontend in HTML/CSS/JS. This allows secure file uploads and processing without embedding Python in JS.

###Design:

Upload section: Drag-and-drop PDF upload with size limit warning (e.g., <500MB).
Processing: Progress bar (updated via WebSockets or polling) showing steps (e.g., "Extracting text... 30%").

###Output: Accordion-style list of sorted segments (metadata as headers: "Date: 2023-01-15 | Type: Lab Report | Provider: Dr. Smith"). Each expands to show text/chunks with "Copy" buttons. Add a timeline visualization (e.g., simple JS chart using Chart.js showing dates).

###Actions: "Download JSON", "Export to CSV" for metadata overview, "Re-process" button for tweaks.

Error Display: User-friendly messages (e.g., "OCR applied to 5 pages due to scans").

###Technology:

Backend: Flask app with endpoints like /upload (processes file, runs Phase 1, returns JSON).

Frontend: HTML/CSS (Tailwind for responsive styling), JS (fetch API for calling backend, handling UI updates).

###Alternative for Simplicity: Use Streamlit (Python-only) for a quick UI—upload button triggers processing, displays results in-app. This skips JS if you want to prototype faster.

###Security: Process files server-side only; delete after session. Remind users this is for local/offline use to avoid PHI risks (no cloud hosting without compliance).


##PHASE 3: TESTING, VALIDATION, AND ITERATION (NEW ADDITION)

Goal: Ensure reliability before full use.

Test with sample data: Use anonymized medical PDFs (e.g., public datasets or synthetic ones). Validate segmentation accuracy (e.g., manual review of 10 files).
Metrics: Accuracy of date extraction (>90%), segment completeness (no mid-report breaks), noise reduction (e.g., % boilerplate removed).

Iteration: Add user feedback loop in UI (e.g., "Flag incorrect segment" button to log issues). Future enhancements: Integrate ML models (e.g., fine-tuned BERT for metadata) or support other formats (Word, images).