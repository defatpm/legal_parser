"""FastAPI application for the medical record processor."""

from __future__ import annotations

import asyncio
import logging
import signal
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ..processors.base import get_processor_registry
from ..utils.config import get_config
from ..utils.exceptions import ValidationError as ProcessorValidationError
from ..utils.logging import get_audit_logger
from .models import (
    APIVersion,
    ConfigurationModel,
    DocumentContent,
    ErrorResponse,
    FileUploadResponse,
    HealthResponse,
    ProcessingQueue,
    ProcessingRequest,
    ProcessingResponse,
    ProcessingResult,
    ProcessingStats,
    ProcessingStatus,
    ProcessorInfo,
    SystemMetrics,
    convert_document_content,
)
from .tasks import TaskManager, get_task_manager, shutdown_task_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get configuration
config = get_config()

# Create a limiter instance
limiter = Limiter(key_func=get_remote_address)


# Event handlers
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Medical Record Processor API")
    await get_task_manager()
    # Start cleanup task
    cleanup_task = asyncio.create_task(cleanup_old_files())

    # Add signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    for signame in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(
            getattr(signal, signame),
            lambda: asyncio.create_task(shutdown_task_manager()),
        )

    logger.info("API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Medical Record Processor API")

    # Cancel cleanup task
    cleanup_task.cancel()

    # Shutdown task manager
    await shutdown_task_manager()

    logger.info("API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Medical Record Processor API",
    description="API for processing medical record PDFs with OCR and text extraction",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add the rate limiter to the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Instrument the app with Prometheus
Instrumentator().instrument(app).expose(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors["origins"] if hasattr(config, "api") else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Audit logging middleware
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    audit_logger = get_audit_logger()
    # Log request
    audit_logger.info(
        f"Request: {request.method} {request.url}",
        extra={
            "request": {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client": request.client.host,
            }
        },
    )

    response = await call_next(request)

    # Log response
    audit_logger.info(
        f"Response: {response.status_code}",
        extra={
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
            }
        },
    )

    return response


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    )
    return response


# Global variables
startup_time = datetime.now()
upload_dir = Path(tempfile.gettempdir()) / "medical_processor_uploads"
upload_dir.mkdir(exist_ok=True)


# Dependency functions
async def get_current_task_manager() -> TaskManager:
    """Get the current task manager."""
    return await get_task_manager()


def validate_file_content(content: bytes) -> None:
    """Validate file content for malicious patterns."""
    # Example: check for common PDF exploits or malicious scripts
    if b"/JavaScript" in content or b"/JS" in content:
        raise HTTPException(
            status_code=400,
            detail="Potentially malicious PDF content detected (JavaScript)",
        )
    if b"/Launch" in content:
        raise HTTPException(
            status_code=400,
            detail="Potentially malicious PDF content detected (Launch Action)",
        )


def validate_file_upload(file: UploadFile) -> None:
    """Validate uploaded file."""
    # Check file extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Check content type - be more lenient for testing
    if file.content_type and file.content_type not in [
        "application/pdf",
        "application/octet-stream",
    ]:
        # For non-PDF files, check filename extension more strictly
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Invalid content type. Only PDF files are supported",
            )


# Background tasks
async def cleanup_old_files():
    """Clean up old uploaded files."""
    while True:
        try:
            # Clean up files older than 24 hours
            cutoff_time = datetime.now().timestamp() - 24 * 3600
            for file_path in upload_dir.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    logger.debug(f"Cleaned up old file: {file_path}")

            # Clean up old tasks
            task_manager = await get_task_manager()
            await task_manager.cleanup_old_tasks(24)

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

        # Sleep for 1 hour
        await asyncio.sleep(3600)


# API Routes


@app.get("/", response_model=APIVersion)
async def root():
    """Get API version and information."""
    return APIVersion(
        version="1.0.0",
        build_date=datetime.now().isoformat(),
        features=[
            "PDF Processing",
            "OCR Support",
            "Async Processing",
            "Batch Processing",
            "Performance Monitoring",
        ],
        endpoints={
            "health": "/health",
            "upload": "/upload",
            "process": "/process",
            "status": "/status/{task_id}",
            "result": "/result/{task_id}",
            "stats": "/stats",
            "docs": "/docs",
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    import psutil

    task_manager = await get_task_manager()
    queue_status = await task_manager.get_queue_status()

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime=(datetime.now() - startup_time).total_seconds(),
        memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024,
        active_tasks=queue_status["processing_tasks"],
        total_processed=queue_status["total_processed"],
    )


@app.get("/health/readiness")
async def readiness_check():
    """Readiness probe."""
    try:
        # Check connections to backing services (e.g., task manager)
        await get_task_manager()
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready") from e


@app.get("/health/liveness")
async def liveness_check():
    """Liveness probe."""
    return {"status": "alive"}


@app.get("/processors", response_model=list[ProcessorInfo])
async def list_processors():
    """List available processors."""
    registry = get_processor_registry()
    processors = []
    for metadata in registry.list_processors():
        processors.append(
            ProcessorInfo(
                name=metadata.name,
                version=metadata.version,
                description=metadata.description,
                input_types=metadata.input_types,
                output_types=metadata.output_types,
                capabilities=metadata.capabilities,
                dependencies=metadata.dependencies,
            )
        )

    return processors


@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(request: Request, file: UploadFile = File(...)) -> FileUploadResponse:
    """Upload a file for processing."""
    validate_file_upload(file)
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf", dir=upload_dir
        ) as tmp_file:
            content = await file.read()
            validate_file_content(content)
            tmp_file.write(content)
            tmp_file.flush()

            return FileUploadResponse(
                filename=file.filename,
                size_bytes=len(content),
                content_type=file.content_type,
                upload_id=Path(tmp_file.name).name,
                expires_at=datetime.now().replace(hour=23, minute=59, second=59),
            )

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="File upload failed") from e


@app.post("/process", response_model=ProcessingResponse)
async def process_document(
    request: Request,
    file: UploadFile = File(...),
    processing_request: ProcessingRequest = Depends(),
) -> ProcessingResponse:
    """Process a document."""
    validate_file_upload(file)
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf", dir=upload_dir
        ) as tmp_file:
            content = await file.read()
            validate_file_content(content)
            tmp_file.write(content)
            tmp_file.flush()

            # Submit processing task
            task_manager = await get_task_manager()
            task_id = await task_manager.submit_task(
                file.filename, Path(tmp_file.name), processing_request
            )

            return ProcessingResponse(
                task_id=task_id,
                status=ProcessingStatus.PENDING,
                message="Document submitted for processing",
                created_at=datetime.now(),
            )

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail="Document processing failed") from e


@app.post("/process/{upload_id}", response_model=ProcessingResponse)
async def process_uploaded_file(upload_id: str, request: ProcessingRequest):
    """Process a previously uploaded file."""
    file_path = upload_dir / upload_id

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # Submit processing task
        task_manager = await get_task_manager()
        task_id = await task_manager.submit_task(upload_id, file_path, request)

        return ProcessingResponse(
            task_id=task_id,
            status=ProcessingStatus.PENDING,
            message="Document submitted for processing",
            created_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Document processing failed") from e


@app.get("/status/{task_id}", response_model=ProcessingResult)
async def get_task_status(task_id: str):
    """Get the status of a processing task."""
    task_manager = await get_task_manager()
    task_info = await task_manager.get_task_status(task_id)

    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")

    return ProcessingResult(
        task_id=task_info.task_id,
        status=task_info.status,
        filename=task_info.filename,
        pages_processed=task_info.total_pages or 0,
        ocr_pages=0,  # Will be calculated from result
        processing_time=task_info.processing_time or 0.0,
        file_size_mb=task_info.file_size_mb or 0.0,
        created_at=task_info.created_at,
        completed_at=task_info.completed_at,
        error_message=task_info.error,
    )


@app.get("/result/{task_id}", response_model=DocumentContent)
async def get_task_result(task_id: str):
    """Get the result of a completed processing task."""
    task_manager = await get_task_manager()
    task_info = await task_manager.get_task_status(task_id)

    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_info.status != ProcessingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Task not completed")

    if not task_info.result:
        raise HTTPException(status_code=500, detail="Result not available")

    return convert_document_content(task_info.result, task_id, task_info.filename)


@app.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a processing task."""
    task_manager = await get_task_manager()
    success = await task_manager.cancel_task(task_id)

    if not success:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")

    return {"message": "Task cancelled successfully"}


@app.get("/queue", response_model=ProcessingQueue)
async def get_queue_status():
    """Get processing queue status."""
    task_manager = await get_task_manager()
    queue_status = await task_manager.get_queue_status()

    return ProcessingQueue(
        queue_size=queue_status["queue_size"],
        processing_tasks=queue_status["processing_tasks"],
        completed_today=queue_status["completed_tasks"],
        average_wait_time=0.0,  # TODO: Calculate
        estimated_processing_time=0.0,  # TODO: Calculate
        active_workers=queue_status["active_workers"],
        max_workers=queue_status["max_workers"],
    )


@app.get("/stats", response_model=ProcessingStats)
async def get_processing_stats():
    """Get processing statistics."""
    task_manager = await get_task_manager()
    stats = await task_manager.get_statistics()

    return ProcessingStats(
        total_requests=stats["total_requests"],
        completed_requests=stats["completed_requests"],
        failed_requests=stats["failed_requests"],
        average_processing_time=stats["average_processing_time"],
        average_file_size_mb=stats["average_file_size_mb"],
        average_pages_per_document=stats["average_pages_per_document"],
        total_pages_processed=stats["total_pages_processed"],
        total_ocr_pages=stats["total_ocr_pages"],
    )


@app.get("/config", response_model=ConfigurationModel)
async def get_configuration():
    """Get current configuration."""
    return ConfigurationModel(
        max_file_size_mb=config.processing.max_file_size_mb,
        max_pages_per_document=1000,  # From config or default
        ocr_enabled=config.pdf_extraction.ocr["enabled"],
        ocr_languages=["eng", "spa", "fra"],  # From config
        supported_formats=["pdf"],
        rate_limit_per_minute=60,
        max_concurrent_tasks=4,
    )


@app.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics():
    """Get system metrics."""
    import psutil

    task_manager = await get_task_manager()
    queue_status = await task_manager.get_queue_status()

    return SystemMetrics(
        cpu_usage_percent=psutil.cpu_percent(),
        memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024,
        memory_available_mb=psutil.virtual_memory().available / 1024 / 1024,
        disk_usage_percent=psutil.disk_usage("/").percent,
        active_connections=0,  # TODO: Track connections
        queue_size=queue_status["queue_size"],
        uptime_seconds=queue_status["uptime_seconds"],
    )


# Error handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details=exc.errors(),
        ).model_dump(mode="json"),
    )


@app.exception_handler(ProcessorValidationError)
async def processor_validation_exception_handler(request, exc):
    """Handle processor validation errors."""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="ProcessorValidationError",
            message=str(exc),
            details=exc.details if hasattr(exc, "details") else None,
        ).model_dump(mode="json"),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error="HTTPException", message=exc.detail).model_dump(
            mode="json"
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError", message="An internal server error occurred"
        ).model_dump(mode="json"),
    )


# Main function for running the server
def main():
    """Run the FastAPI server."""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        timeout_graceful_shutdown=30,
    )


if __name__ == "__main__":
    main()
