#!/usr/bin/env python3
"""
ITR Report Viewer Server

Web application for viewing ITR Economics reports with:
- PDF display alongside extracted data
- LLM chart interpretations
- Ask AI feature for comparisons and analysis
- Link back to original PDF pages

Usage:
    python viewer/server.py

    # Or with uvicorn
    uvicorn viewer.server:app --host 0.0.0.0 --port 8080 --reload
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
import httpx

# Load environment variables
load_dotenv()

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.flow_extractor import FlowExtractor
from src.llm_extractor import LLMExtractor

# Configuration
MONGODB_URI = os.getenv("ITR_MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("ITR_DATABASE_NAME", "ITRReports")
FILES_DIR = PROJECT_ROOT / "Files"
OUTPUT_DIR = PROJECT_ROOT / "output"
VIEWER_DIR = Path(__file__).parent

# Azure OpenAI config for Ask AI
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")


class AskRequest(BaseModel):
    question: str
    report_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class AskResponse(BaseModel):
    response: str
    page_references: Optional[List[int]] = None
    sources: Optional[List[str]] = None


# Initialize FastAPI
app = FastAPI(
    title="ITR Report Viewer",
    description="View and analyze ITR Economics reports with AI assistance",
    version="3.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory=VIEWER_DIR / "static"), name="static")
templates = Jinja2Templates(directory=VIEWER_DIR / "templates")

# MongoDB connection
mongo_client = None
db = None
llm = None


@app.on_event("startup")
async def startup():
    global mongo_client, db, llm

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
        print("LLM Extractor initialized")
    except Exception as e:
        print(f"Warning: LLM initialization failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    if mongo_client:
        mongo_client.close()
    if llm:
        llm.close()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main viewer page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/files/{filename:path}")
async def serve_pdf(filename: str):
    """Serve PDF files."""
    file_path = FILES_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@app.get("/api/reports")
async def list_reports():
    """List all processed reports."""
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
    ).sort("metadata.extraction_date", -1)

    reports = []
    for doc in cursor:
        reports.append({
            "report_id": doc["report_id"],
            "pdf_filename": doc["pdf_filename"],
            "report_period": doc.get("report_period"),
            "total_pages": doc.get("metadata", {}).get("total_pages", 0),
            "total_series": len(doc.get("series_index", [])),
            "total_charts": doc.get("metadata", {}).get("total_charts", 0),
            "extraction_date": doc.get("metadata", {}).get("extraction_date")
        })

    return reports


@app.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    """Get a specific report with all data."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    # Convert ObjectId
    doc["_id"] = str(doc["_id"])

    return doc


@app.post("/api/ask", response_model=AskResponse)
async def ask_ai(request: AskRequest):
    """Ask AI about the report - enables comparison with PDF."""
    if not AZURE_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    # Build context from report
    report_context = ""
    page_references = []

    if request.report_id and db is not None:
        coll = db["ITRextract_Flow"]
        doc = coll.find_one({"report_id": request.report_id})

        if doc:
            # Build a summary of the report for context
            series_list = doc.get("series_index", [])
            report_context = f"""
Report: {doc.get('pdf_filename')}
Period: {doc.get('report_period', 'Unknown')}
Total Pages: {doc.get('metadata', {}).get('total_pages', 0)}
Series Extracted: {len(series_list)}
Series Names: {', '.join(series_list[:20])}{'...' if len(series_list) > 20 else ''}

Document Flow Summary:
"""
            # Add key information from each page
            for page in doc.get("document_flow", [])[:30]:  # Limit context size
                page_num = page.get("page_number", 0)
                series_name = page.get("series_name", "Unknown")

                # Get chart interpretations
                for block in page.get("blocks", []):
                    if block.get("block_type") == "chart" and block.get("interpretation"):
                        interp = block["interpretation"]
                        report_context += f"""
Page {page_num} - {series_name}:
- Trend: {interp.get('trend_direction', 'unknown')}
- Phase: {interp.get('current_phase', 'unknown')}
- Analysis: {interp.get('description', 'No description')[:200]}
- Implications: {interp.get('business_implications', 'None')[:200]}
"""
                        page_references.append(page_num)

    # Build the prompt
    system_prompt = """You are an expert economic analyst helping users understand ITR Economics reports.
You have access to extracted data from PDF reports including:
- Series data with forecasts
- Chart interpretations from GPT-4 Vision analysis
- Business cycle phases (A=Recovery, B=Accelerating, C=Slowing, D=Recession)

When answering:
1. Reference specific page numbers when discussing data
2. Compare extracted data accuracy when asked
3. Highlight key economic trends and implications
4. Provide actionable business insights
5. If asked to compare with PDF, explain what was extracted and any potential discrepancies

Format responses with clear sections and bullet points when appropriate."""

    user_prompt = f"""Context from the ITR Report:
{report_context}

User's Question: {request.question}

Additional Context: {json.dumps(request.context) if request.context else 'None'}

Please provide a helpful analysis."""

    # Call Azure OpenAI
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{AZURE_ENDPOINT}?api-version={AZURE_API_VERSION}",
                headers={
                    "Content-Type": "application/json",
                    "api-key": AZURE_API_KEY
                },
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.3
                }
            )

            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="AI service error")

            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]

            return AskResponse(
                response=ai_response,
                page_references=list(set(page_references))[:10],  # Unique pages
                sources=[request.report_id] if request.report_id else None
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI request failed: {str(e)}")


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF through the workflow."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Save file
    import uuid
    safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    pdf_path = FILES_DIR / safe_filename

    content = await file.read()
    with open(pdf_path, "wb") as f:
        f.write(content)

    try:
        # Process with flow extractor
        with FlowExtractor(pdf_path, llm) as extractor:
            document = extractor.extract_full_document_flow()

        # Store in MongoDB
        if db is not None:
            coll = db["ITRextract_Flow"]
            coll.update_one(
                {"report_id": document["report_id"]},
                {"$set": document},
                upsert=True
            )

        # Count interpretations
        total_interpretations = 0
        for page in document.get("document_flow", []):
            for block in page.get("blocks", []):
                if block.get("interpretation"):
                    total_interpretations += 1

        return {
            "success": True,
            "message": "PDF processed successfully",
            "report_id": document["report_id"],
            "filename": file.filename,
            "statistics": {
                "total_pages": document["metadata"]["total_pages"],
                "total_series": len(document.get("series_index", [])),
                "total_charts": document["metadata"]["total_charts"],
                "llm_interpretations": total_interpretations
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("ITR_VIEWER_PORT", 8081))
    host = os.getenv("ITR_VIEWER_HOST", "0.0.0.0")

    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║              ITR Report Viewer v3.0.0                        ║
    ║         View, Compare, and Analyze with AI                   ║
    ╚══════════════════════════════════════════════════════════════╝

    Starting viewer at http://{host}:{port}

    Features:
      - Side-by-side PDF and extracted data view
      - LLM chart interpretations with business insights
      - Ask AI for comparisons and analysis
      - Link extracted data back to PDF pages

    Open in browser: http://localhost:{port}
    """)

    uvicorn.run(app, host=host, port=port)
