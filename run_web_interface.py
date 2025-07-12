#!/usr/bin/env python3
"""Script to run the Streamlit web interface."""

import subprocess
import sys
from pathlib import Path


def main():
    """Run the Streamlit web interface."""
    # Get the path to the web interface module
    web_interface_path = Path(__file__).parent / "src" / "interfaces" / "web" / "app.py"
    # Check if the file exists
    if not web_interface_path.exists():
        print(f"Error: Web interface file not found at {web_interface_path}")
        sys.exit(1)
    # Run Streamlit
    try:
        print("Starting Medical Record Processor Web Interface...")
        print("Opening browser at http://localhost:8501")
        print("Press Ctrl+C to stop the server")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(web_interface_path),
                "--server.port=8501",
                "--server.address=0.0.0.0",
                "--browser.gatherUsageStats=false",
            ],
            check=True,
        )
    except KeyboardInterrupt:
        print("\nShutting down web interface...")
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
