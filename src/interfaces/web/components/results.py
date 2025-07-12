import json

import pandas as pd
import streamlit as st

from src.interfaces.web.utils import create_batch_zip, data_to_csv


def display_results(data: dict, filename: str):
    """Display processing results in tabs."""
    tabs = st.tabs(["Summary", "Segments", "Timeline", "Raw JSON", "Export"])

    with tabs[0]:
        st.subheader("Summary")
        st.write(f"Document: {filename}")
        st.write(f"Pages: {data.get('page_count', 'N/A')}")
        st.write(f"Segments: {len(data.get('segments', []))}")
        st.write(f"Timeline Events: {len(data.get('timeline', []))}")

    with tabs[1]:
        st.subheader("Segments")
        if "segments" in data:
            df = pd.DataFrame(data["segments"])
            st.dataframe(df)

    with tabs[2]:
        st.subheader("Timeline")
        if "timeline" in data:
            df = pd.DataFrame(data["timeline"])
            st.dataframe(df)
            st.line_chart(
                df.set_index("date")["confidence"] if "confidence" in df else None
            )

    with tabs[3]:
        st.subheader("Raw JSON")
        st.json(data)

    with tabs[4]:
        st.subheader("Export Options")
        st.download_button(
            "JSON", json.dumps(data, indent=2), f"{filename}_processed.json"
        )
        st.download_button(
            "Segments CSV",
            data_to_csv(data.get("segments", [])),
            f"{filename}_segments.csv",
        )
        st.download_button(
            "Timeline CSV",
            data_to_csv(data.get("timeline", [])),
            f"{filename}_timeline.csv",
        )


def display_batch_results(results: list[dict]):
    """Display batch results."""
    st.subheader("Batch Results")
    df = pd.DataFrame(
        [{"filename": r["filename"], "status": r["status"]} for r in results]
    )
    st.dataframe(df)

    zip_data = create_batch_zip(results)
    st.download_button("Download ZIP", zip_data, "batch_results.zip")
