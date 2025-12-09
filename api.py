#!/usr/bin/env python3
"""
ITRImport API Server

FastAPI application that accepts PDF uploads and launches the ITR workflow.
Designed to be called from a portal application.

Usage:
    # Start the server
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload

    # Or run directly
    python api.py

Endpoints:
    POST /upload          - Upload PDF and process through workflow
    POST /upload/async    - Upload PDF and process asynchronously (returns job ID)
    GET  /status/{job_id} - Check status of async job
    GET  /reports         - List all processed reports
    GET  /reports/{id}    - Get specific report data
    GET  /health          - Health check endpoint
"""

import os
import sys
import uuid
import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.flow_extractor import FlowExtractor
from src.llm_extractor import LLMExtractor

# Configuration
UPLOAD_DIR = Path(os.getenv("ITR_UPLOAD_DIR", "Files"))
OUTPUT_DIR = Path(os.getenv("ITR_OUTPUT_DIR", "output"))
MONGODB_URI = os.getenv("ITR_MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("ITR_DATABASE_NAME", "ITRReports")
MAX_FILE_SIZE = int(os.getenv("ITR_MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB default

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingJob(BaseModel):
    """Model for tracking async processing jobs."""
    job_id: str
    filename: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class UploadResponse(BaseModel):
    """Response model for PDF upload."""
    success: bool
    message: str
    report_id: Optional[str] = None
    filename: Optional[str] = None
    statistics: Optional[Dict[str, Any]] = None


class AsyncUploadResponse(BaseModel):
    """Response model for async PDF upload."""
    job_id: str
    message: str
    status_url: str


class ReportSummary(BaseModel):
    """Summary model for a processed report."""
    report_id: str
    pdf_filename: str
    report_period: Optional[str] = None
    total_pages: int = 0
    total_series: int = 0
    total_charts: int = 0
    extraction_date: Optional[datetime] = None


# In-memory job storage (use Redis in production)
jobs: Dict[str, ProcessingJob] = {}

# MongoDB client (initialized on startup)
mongo_client: Optional[MongoClient] = None
db = None
llm: Optional[LLMExtractor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global mongo_client, db, llm

    # Startup
    print("Starting ITRImport API Server...")

    # Connect to MongoDB
    try:
        mongo_client = MongoClient(MONGODB_URI)
        db = mongo_client[DATABASE_NAME]
        print(f"Connected to MongoDB: {DATABASE_NAME}")
    except Exception as e:
        print(f"Warning: MongoDB connection failed: {e}")

    # Initialize LLM
    try:
        llm = LLMExtractor()
        print("LLM Extractor initialized (Azure OpenAI GPT-4)")
    except Exception as e:
        print(f"Warning: LLM initialization failed: {e}")

    yield

    # Shutdown
    print("Shutting down ITRImport API Server...")
    if mongo_client:
        mongo_client.close()
    if llm:
        llm.close()


# Create FastAPI app
app = FastAPI(
    title="ITRImport API",
    description="API for uploading and processing ITR Economics PDF reports",
    version="3.0.0",
    lifespan=lifespan
)

# Configure CORS for portal access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def process_pdf_sync(pdf_path: Path, use_llm: bool = True) -> Dict[str, Any]:
    """Process a PDF synchronously and return results."""
    global llm, db

    extractor_llm = llm if use_llm else None

    with FlowExtractor(pdf_path, extractor_llm) as extractor:
        document = extractor.extract_full_document_flow()

    # Store in MongoDB if available
    if db is not None:
        coll = db["ITRextract_Flow"]
        coll.update_one(
            {"report_id": document["report_id"]},
            {"$set": document},
            upsert=True
        )

    # Save to JSON file
    output_dir = OUTPUT_DIR / "flow"
    output_dir.mkdir(parents=True, exist_ok=True)

    import json
    output_file = output_dir / f"{document['report_id']}_flow.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, ensure_ascii=False, default=str)

    # Build statistics
    total_interpretations = 0
    for page in document.get("document_flow", []):
        for block in page.get("blocks", []):
            if block.get("interpretation"):
                total_interpretations += 1

    return {
        "report_id": document["report_id"],
        "pdf_filename": document["pdf_filename"],
        "report_period": document.get("report_period"),
        "statistics": {
            "total_pages": document["metadata"]["total_pages"],
            "total_series": len(document.get("series_index", [])),
            "total_charts": document["metadata"]["total_charts"],
            "llm_interpretations": total_interpretations
        },
        "output_file": str(output_file)
    }


async def process_pdf_async(job_id: str, pdf_path: Path, use_llm: bool = True):
    """Process a PDF asynchronously and update job status."""
    global jobs

    job = jobs.get(job_id)
    if not job:
        return

    try:
        job.status = JobStatus.PROCESSING
        job.message = "Processing PDF..."
        job.updated_at = datetime.utcnow()

        # Run processing in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            process_pdf_sync,
            pdf_path,
            use_llm
        )

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.message = "Processing complete"
        job.result = result
        job.updated_at = datetime.utcnow()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"Processing failed: {str(e)}"
        job.updated_at = datetime.utcnow()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    mongo_status = "connected" if db is not None else "disconnected"
    llm_status = "initialized" if llm is not None else "not initialized"

    return {
        "status": "healthy",
        "version": "3.0.0",
        "mongodb": mongo_status,
        "llm": llm_status,
        "upload_dir": str(UPLOAD_DIR),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    use_llm: bool = Query(True, description="Use LLM for enhanced extraction")
):
    """
    Upload a PDF and process it synchronously through the workflow.

    Returns the processing results immediately (may take several minutes for large PDFs).
    For large files or when you need immediate response, use /upload/async instead.
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
        )

    # Save uploaded file
    safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    pdf_path = UPLOAD_DIR / safe_filename

    try:
        with open(pdf_path, "wb") as f:
            f.write(content)

        # Process the PDF
        result = process_pdf_sync(pdf_path, use_llm)

        return UploadResponse(
            success=True,
            message="PDF processed successfully",
            report_id=result["report_id"],
            filename=file.filename,
            statistics=result["statistics"]
        )

    except Exception as e:
        # Clean up on error
        if pdf_path.exists():
            pdf_path.unlink()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/upload/async", response_model=AsyncUploadResponse)
async def upload_pdf_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    use_llm: bool = Query(True, description="Use LLM for enhanced extraction")
):
    """
    Upload a PDF and process it asynchronously.

    Returns immediately with a job ID. Use /status/{job_id} to check progress.
    Recommended for large PDFs or when immediate response is needed.
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
        )

    # Save uploaded file
    job_id = uuid.uuid4().hex
    safe_filename = f"{job_id[:8]}_{file.filename}"
    pdf_path = UPLOAD_DIR / safe_filename

    with open(pdf_path, "wb") as f:
        f.write(content)

    # Create job
    job = ProcessingJob(
        job_id=job_id,
        filename=file.filename,
        status=JobStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        message="Queued for processing"
    )
    jobs[job_id] = job

    # Start background processing
    background_tasks.add_task(process_pdf_async, job_id, pdf_path, use_llm)

    return AsyncUploadResponse(
        job_id=job_id,
        message="PDF uploaded successfully. Processing started.",
        status_url=f"/status/{job_id}"
    )


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of an async processing job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.job_id,
        "filename": job.filename,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "result": job.result if job.status == JobStatus.COMPLETED else None,
        "error": job.error if job.status == JobStatus.FAILED else None
    }


@app.get("/reports", response_model=List[ReportSummary])
async def list_reports(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """List all processed reports from MongoDB."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    cursor = coll.find(
        {},
        {
            "report_id": 1,
            "pdf_filename": 1,
            "report_period": 1,
            "metadata": 1,
            "series_index": 1
        }
    ).skip(skip).limit(limit).sort("metadata.extraction_date", -1)

    reports = []
    for doc in cursor:
        reports.append(ReportSummary(
            report_id=doc["report_id"],
            pdf_filename=doc["pdf_filename"],
            report_period=doc.get("report_period"),
            total_pages=doc.get("metadata", {}).get("total_pages", 0),
            total_series=len(doc.get("series_index", [])),
            total_charts=doc.get("metadata", {}).get("total_charts", 0),
            extraction_date=doc.get("metadata", {}).get("extraction_date")
        ))

    return reports


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get a specific report by ID."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    # Convert ObjectId to string for JSON serialization
    doc["_id"] = str(doc["_id"])

    return doc


@app.get("/reports/{report_id}/charts")
async def get_report_charts(report_id: str):
    """Get all chart interpretations for a report."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    charts = []
    for page in doc.get("document_flow", []):
        for block in page.get("blocks", []):
            if block.get("block_type") == "chart":
                charts.append({
                    "page_number": page.get("page_number"),
                    "series_name": page.get("series_name"),
                    "chart_type": block.get("content", {}).get("chart_type"),
                    "interpretation": block.get("interpretation"),
                    "metadata": block.get("metadata")
                })

    return {
        "report_id": report_id,
        "total_charts": len(charts),
        "charts": charts
    }


@app.get("/reports/{report_id}/series")
async def get_report_series(report_id: str):
    """Get all series from a report."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one(
        {"report_id": report_id},
        {"series_index": 1, "document_flow.series_name": 1}
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "report_id": report_id,
        "series": doc.get("series_index", [])
    }


@app.delete("/reports/{report_id}")
async def delete_report(report_id: str):
    """Delete a report from the database."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    result = coll.delete_one({"report_id": report_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"message": f"Report {report_id} deleted successfully"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("ITR_API_PORT", 8000))
    host = os.getenv("ITR_API_HOST", "0.0.0.0")

    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║              ITRImport API Server v3.0.0                     ║
    ║         PDF Upload & Workflow Processing API                 ║
    ╚══════════════════════════════════════════════════════════════╝

    Starting server at http://{host}:{port}

    Endpoints:
      POST /upload          - Upload and process PDF (sync)
      POST /upload/async    - Upload and process PDF (async)
      GET  /status/{{job_id}} - Check async job status
      GET  /reports         - List all reports
      GET  /reports/{{id}}    - Get specific report
      GET  /health          - Health check

    Documentation: http://{host}:{port}/docs
    """)

    uvicorn.run(app, host=host, port=port)
