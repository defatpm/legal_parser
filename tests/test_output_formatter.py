import csv
import io
from datetime import datetime

from openpyxl import load_workbook

from src.models.document import DocumentSegment
from src.utils.output_formatter import to_csv_string, to_excel


def test_to_csv_string():
    """Test converting segments to CSV string."""
    segments = [
        DocumentSegment(
            segment_id="1",
            text_content="Segment 1",
            page_start=1,
            page_end=1,
            date_of_service=datetime(2023, 1, 1),
            metadata={"detected_header": "Header 1"},
        ),
        DocumentSegment(
            segment_id="2",
            text_content="Segment 2",
            page_start=2,
            page_end=2,
            date_of_service=datetime(2023, 1, 2),
            metadata={"detected_header": "Header 2"},
        ),
    ]

    csv_string = to_csv_string(segments)
    reader = csv.reader(io.StringIO(csv_string))

    # Check header
    header = next(reader)
    assert header == [
        "segment_id",
        "date_of_service",
        "page_start",
        "page_end",
        "detected_header",
        "text_content",
    ]

    # Check data
    row1 = next(reader)
    assert row1 == ["1", "2023-01-01T00:00:00", "1", "1", "Header 1", "Segment 1"]
    row2 = next(reader)
    assert row2 == ["2", "2023-01-02T00:00:00", "2", "2", "Header 2", "Segment 2"]


def test_to_excel():
    """Test converting segments to Excel file."""
    segments = [
        DocumentSegment(
            segment_id="1",
            text_content="Segment 1",
            page_start=1,
            page_end=1,
            date_of_service=datetime(2023, 1, 1),
            metadata={"detected_header": "Header 1"},
        ),
        DocumentSegment(
            segment_id="2",
            text_content="Segment 2",
            page_start=2,
            page_end=2,
            date_of_service=datetime(2023, 1, 2),
            metadata={"detected_header": "Header 2"},
        ),
    ]

    excel_data = to_excel(segments)
    workbook = load_workbook(io.BytesIO(excel_data))
    sheet = workbook.active

    # Check header
    header = [cell.value for cell in sheet[1]]
    assert header == [
        "Segment ID",
        "Date of Service",
        "Page Start",
        "Page End",
        "Detected Header",
        "Text Content",
    ]

    # Check data
    row1 = [cell.value for cell in sheet[2]]
    assert row1 == ["1", datetime(2023, 1, 1), 1, 1, "Header 1", "Segment 1"]
    row2 = [cell.value for cell in sheet[3]]
    assert row2 == ["2", datetime(2023, 1, 2), 2, 2, "Header 2", "Segment 2"]
