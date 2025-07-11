# Web Interface Documentation

The Medical Record Processor includes a comprehensive web interface built with Streamlit that provides an intuitive, user-friendly way to process medical documents.

## Features

### 🎯 Core Functionality
- **Single Document Processing**: Upload and process individual PDF files
- **Batch Processing**: Upload and process multiple PDF files simultaneously
- **Real-time Progress Tracking**: Monitor processing status with progress bars and ETA
- **Results Visualization**: Interactive display of processing results
- **Export Options**: Download results in JSON, CSV, and ZIP formats

### 📋 Interface Pages

#### 1. Single Document Processing
- **File Upload**: Drag-and-drop or click to upload PDF files
- **Processing Status**: Real-time progress indicator with status messages
- **Results Tabs**:
  - **Summary**: Document overview with key metrics
  - **Segments**: Individual document sections with filtering
  - **Timeline**: Chronological events with visualization
  - **Raw JSON**: Complete processing output
  - **Export**: Download options for various formats

#### 2. Batch Processing
- **Multiple File Upload**: Select multiple PDF files at once
- **Concurrent Processing**: Configurable number of worker threads
- **Progress Monitoring**: Real-time batch progress with statistics
- **Results Management**: Comprehensive batch results with export options

#### 3. Processing History
- **Session Tracking**: View all processed documents in current session
- **Batch History**: Review previous batch processing operations
- **Reprocessing**: Option to reprocess documents
- **History Management**: Clear individual or all history records

#### 4. Settings & Configuration
- **Configuration Display**: View current system settings
- **System Information**: Processing pipeline and format details
- **Help Documentation**: Usage instructions and troubleshooting

## Getting Started

### Prerequisites
- Python 3.8+
- All project dependencies installed (`pip install -r requirements.txt`)

### Running the Web Interface

#### Option 1: Using the Startup Script
```bash
python run_web_interface.py
```

#### Option 2: Direct Streamlit Command
```bash
streamlit run src/web_interface.py
```

#### Option 3: Custom Configuration
```bash
streamlit run src/web_interface.py --server.port=8501 --server.address=0.0.0.0
```

### Accessing the Interface
1. Open your web browser
2. Navigate to `http://localhost:8501`
3. The interface will load automatically

## Usage Guide

### Processing a Single Document

1. **Navigate to Single Document Page**
   - Click "Single Document" in the sidebar

2. **Upload PDF File**
   - Click "Browse files" or drag-and-drop a PDF file
   - File information will be displayed

3. **Process Document**
   - Click "🚀 Process Document"
   - Monitor progress with the progress bar
   - Processing status will update in real-time

4. **View Results**
   - Results appear in tabbed interface below
   - Explore different views: Summary, Segments, Timeline, Raw JSON

5. **Export Results**
   - Go to "Export" tab
   - Choose format: JSON, CSV, or Timeline CSV
   - Click download buttons

### Batch Processing Multiple Documents

1. **Navigate to Batch Processing Page**
   - Click "Batch Processing" in the sidebar

2. **Upload Multiple Files**
   - Click "Browse files" and select multiple PDF files
   - Or drag-and-drop multiple files at once

3. **Configure Processing**
   - Set number of concurrent workers (1-8)
   - Enable/disable progress tracking
   - Review file list in expandable section

4. **Process Batch**
   - Click "🚀 Process Batch"
   - Monitor real-time progress and statistics
   - View completion rates and ETA

5. **Review Results**
   - View batch statistics and performance metrics
   - Examine individual file results in the results table
   - Export summary CSV or download all results as ZIP

### Viewing Processing History

1. **Navigate to Processing History Page**
   - Click "Processing History" in the sidebar

2. **Review Past Operations**
   - Single document history shows individual files
   - Batch history shows batch operations
   - Expand items to see detailed metrics

3. **Manage History**
   - Reprocess documents by clicking "🔄 Reprocess"
   - Clear history with "🗑️ Clear History" buttons

## Features in Detail

### Real-time Processing Status
- **Progress Bars**: Visual indication of processing progress
- **Status Messages**: Descriptive updates on current processing step
- **ETA Calculation**: Estimated time to completion for batches
- **Performance Metrics**: Throughput and timing statistics

### Results Visualization
- **Interactive Tables**: Sortable and filterable data displays
- **JSON Formatting**: Syntax-highlighted JSON output
- **Timeline Charts**: Visual representation of chronological events
- **Segment Filtering**: Filter by type, length, and other criteria

### Export Options
- **JSON Export**: Complete processing results in JSON format
- **CSV Export**: Structured data in CSV format for analysis
- **Timeline CSV**: Chronological events as CSV
- **ZIP Archives**: Batch results bundled in ZIP files

### Error Handling
- **Graceful Failures**: Clear error messages for failed processing
- **Retry Options**: Ability to reprocess failed documents
- **Status Tracking**: Clear indication of success/failure states

## Configuration

### System Settings
The web interface respects the system configuration in `config.yaml`:
- Processing timeouts
- Worker thread limits
- File size limits
- Performance settings

### UI Customization
- **Responsive Design**: Works on desktop and mobile devices
- **Dark/Light Theme**: Follows system preferences
- **Customizable Layout**: Expandable sections and tabs

## Troubleshooting

### Common Issues

#### Interface Won't Start
```bash
# Check if Streamlit is installed
pip install streamlit

# Try running with verbose output
streamlit run src/web_interface.py --logger.level=debug
```

#### Processing Failures
- Check file size limits (default: 100MB)
- Verify PDF file is not corrupted
- Monitor system resources during processing
- Review error messages in interface

#### Performance Issues
- Reduce concurrent workers for batch processing
- Clear processing history regularly
- Monitor system memory usage
- Process smaller batches if needed

#### Upload Issues
- Ensure file is PDF format
- Check file permissions
- Verify file size is within limits
- Try refreshing the page

### Performance Tips
- **Batch Processing**: Use batch mode for multiple files
- **Worker Threads**: Adjust based on system capabilities
- **Memory Management**: Clear history for long sessions
- **File Sizes**: Process large files individually

## Development

### Adding New Features
1. **Page Structure**: Add new pages in `_run()` method
2. **Session State**: Manage state in `__init__()` method
3. **UI Components**: Use Streamlit components for consistency
4. **Error Handling**: Implement graceful error handling

### Testing
```bash
# Run web interface tests
pytest tests/test_web_interface.py -v

# Run with coverage
pytest tests/test_web_interface.py --cov=src.web_interface
```

### Customization
- **Styling**: Modify CSS in `run()` method
- **Layout**: Adjust column layouts and component placement
- **Functionality**: Add new processing features
- **Export Formats**: Implement additional export options

## API Integration

The web interface can be extended to work with the REST API:
- Background processing via API calls
- Status polling for long-running operations
- Remote processing capabilities
- Multi-user support

## Security Considerations

- **File Upload**: Only accepts PDF files
- **Processing**: Runs in isolated environment
- **Data Storage**: Temporary files are cleaned up
- **Session Management**: Data stored in browser session only

## Support

For issues or feature requests:
1. Check the troubleshooting section
2. Review system logs
3. Test with sample files
4. Report issues with detailed information

## Version History

- **v1.0**: Initial web interface implementation
- **v1.1**: Added batch processing support
- **v1.2**: Enhanced export options
- **v1.3**: Improved error handling and UI