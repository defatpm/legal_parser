from __future__ import annotations

import csv
import io

from ..models.document import DocumentSegment


def to_csv_string(segments: list[DocumentSegment]) -> str:
    """Converts a list of DocumentSegments to a CSV formatted string.

    Args:
        segments: A list of DocumentSegment objects.

    Returns:
        A string in CSV format.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "segment_id",
            "date_of_service",
            "page_start",
            "page_end",
            "detected_header",
            "text_content",
        ]
    )

    # Write data
    for segment in segments:
        writer.writerow(
            [
                segment.segment_id,
                segment.date_of_service.isoformat() if segment.date_of_service else "",
                segment.page_start,
                segment.page_end,
                segment.metadata.get("detected_header", ""),
                segment.text_content,
            ]
        )

    return output.getvalue()


def to_excel(segments: list[DocumentSegment]) -> bytes:
    """Converts a list of DocumentSegments to an Excel file in memory.

    Args:
        segments: A list of DocumentSegment objects.

    Returns:
        A byte string representing the Excel file.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Segments"

    # Write header
    headers = [
        "Segment ID",
        "Date of Service",
        "Page Start",
        "Page End",
        "Detected Header",
        "Text Content",
    ]
    ws.append(headers)

    # Style header
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    # Write data
    for segment in segments:
        ws.append(
            [
                segment.segment_id,
                segment.date_of_service,
                segment.page_start,
                segment.page_end,
                segment.metadata.get("detected_header", ""),
                segment.text_content,
            ]
        )

    # Adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter  # Get the column name
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except (ValueError, TypeError):
                pass
        adjusted_width = max_length + 2
        ws.column_dimensions[column].width = adjusted_width

    # Save to an in-memory buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()
