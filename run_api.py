#!/usr/bin/env python3
"""Script to run the Medical Record Processor API server."""

import sys
from pathlib import Path

import uvicorn

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.api.main import app


def main():
    """Run the API server."""
    print("Starting Medical Record Processor API...")
    print("API Documentation will be available at: http://localhost:8000/docs")
    print("Health check: http://localhost:8000/health")
    print("Press Ctrl+C to stop the server")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, log_level="info")


if __name__ == "__main__":
    main()
