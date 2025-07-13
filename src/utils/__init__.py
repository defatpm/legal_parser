"""Utility functions for the legal parser."""

# Import utility functions to make them available at package level
try:
    # Import from utils.py if it exists
    from ..utils import create_batch_zip, data_to_csv
except ImportError:
    # Fall back to utils submodules if available
    try:
        # Define a simple CSV function for generic data
        import csv
        from io import StringIO

        def data_to_csv(data):
            """Convert list of dicts to CSV string."""
            if not data:
                return ""
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()

    except ImportError:
        pass

    try:
        # Define create_batch_zip if not available elsewhere
        import json
        import zipfile
        from io import BytesIO

        def create_batch_zip(results):
            """Create ZIP archive of batch results."""
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for result in results:
                    if result.get("status") == "completed" and result.get("data"):
                        zipf.writestr(
                            f"{result['filename']}_processed.json",
                            json.dumps(result["data"], indent=2),
                        )
            zip_buffer.seek(0)
            return zip_buffer.read()

    except ImportError:
        pass
