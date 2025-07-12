import csv
import json
import zipfile
from io import BytesIO, StringIO


def data_to_csv(data: list[dict]) -> str:
    """Convert list of dicts to CSV string."""
    if not data:
        return ""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def create_batch_zip(results: list[dict]) -> bytes:
    """Create ZIP archive of batch results."""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for result in results:
            if result["status"] == "completed":
                zipf.writestr(
                    f"{result['filename']}_processed.json",
                    json.dumps(result["data"], indent=2),
                )
    zip_buffer.seek(0)
    return zip_buffer.read()
