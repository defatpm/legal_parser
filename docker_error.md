AttributeError: 'PosixPath' object has no attribute 'get'
Traceback:
File "/app/src/interfaces/web/app.py", line 78, in <module>
    run_app()
File "/app/src/interfaces/web/app.py", line 68, in run_app
    single_document_page()
File "/app/src/interfaces/web/pages/single_document.py", line 56, in single_document_page
    display_results(result, uploaded_file.name)
File "/app/src/interfaces/web/components/results.py", line 16, in display_results
    st.write(f"Pages: {data.get('page_count', 'N/A')}")
                       ^^^^^^^^
