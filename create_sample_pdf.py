#!/usr/bin/env python3
"""Create a sample PDF for testing purposes."""

import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_sample_pdf():
    """Create a sample medical record PDF."""

    # Read the sample text
    sample_file = Path("data/sample/sample_medical_record.txt")
    if not sample_file.exists():
        print(f"Sample file not found: {sample_file}")
        return False

    with open(sample_file) as f:
        content = f.read()

    # Create PDF
    pdf_path = Path("data/sample/sample_medical_record.pdf")
    pdf_path.parent.mkdir(exist_ok=True)

    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter

    # Split content into lines
    lines = content.split("\n")

    # Starting position
    x = 50
    y = height - 50
    line_height = 12

    # Add content to PDF
    for line in lines:
        # Check if we need a new page
        if y < 50:
            c.showPage()
            y = height - 50

        # Handle long lines
        if len(line) > 80:
            # Split long lines
            words = line.split(" ")
            current_line = ""
            for word in words:
                if len(current_line + word) < 80:
                    current_line += word + " "
                else:
                    c.drawString(x, y, current_line.strip())
                    y -= line_height
                    current_line = word + " "

            if current_line:
                c.drawString(x, y, current_line.strip())
                y -= line_height
        else:
            c.drawString(x, y, line)
            y -= line_height

    c.save()
    print(f"✓ Sample PDF created: {pdf_path}")
    return True


if __name__ == "__main__":
    # Try to create PDF with reportlab
    try:
        if create_sample_pdf():
            print("Sample PDF creation successful!")
        else:
            print("Sample PDF creation failed!")
    except ImportError:
        print("reportlab not installed. Installing...")
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
        create_sample_pdf()
    except Exception as e:
        print(f"Error creating PDF: {e}")
        sys.exit(1)
