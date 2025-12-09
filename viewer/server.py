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
from src.analysis_generator import AnalysisGenerator

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


# ============================================================================
# Analysis API Endpoints (US1, US2, US3)
# ============================================================================

@app.get("/api/reports/{report_id}/analysis")
async def get_report_analysis(report_id: str):
    """Get complete analysis for a report."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "report_id": report_id,
        "overall_analysis": doc.get("overall_analysis"),
        "sector_analyses": doc.get("sector_analyses"),
        "analysis_metadata": doc.get("analysis_metadata")
    }


@app.get("/api/reports/{report_id}/analysis/overall")
async def get_overall_analysis(report_id: str):
    """Get only overall analysis."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one(
        {"report_id": report_id},
        {"overall_analysis": 1}
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    return doc.get("overall_analysis")


@app.get("/api/reports/{report_id}/analysis/sentiment")
async def get_sentiment_score(report_id: str):
    """Get sentiment score only."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one(
        {"report_id": report_id},
        {"overall_analysis.sentiment_score": 1}
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    overall = doc.get("overall_analysis", {})
    return overall.get("sentiment_score")


@app.get("/api/reports/{report_id}/analysis/themes")
async def get_key_themes(report_id: str):
    """Get key themes only."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one(
        {"report_id": report_id},
        {"overall_analysis.key_themes": 1}
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    overall = doc.get("overall_analysis", {})
    return overall.get("key_themes", [])


@app.get("/api/reports/{report_id}/analysis/sectors")
async def get_all_sector_analyses(report_id: str):
    """Get all sector analyses."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one(
        {"report_id": report_id},
        {"sector_analyses": 1}
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    return doc.get("sector_analyses", {})


@app.get("/api/reports/{report_id}/analysis/sectors/{sector}")
async def get_sector_analysis(report_id: str, sector: str):
    """Get analysis for a specific sector."""
    valid_sectors = ["core", "financial", "construction", "manufacturing"]
    if sector not in valid_sectors:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sector. Must be one of: {', '.join(valid_sectors)}"
        )

    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one(
        {"report_id": report_id},
        {f"sector_analyses.{sector}": 1}
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    sector_analyses = doc.get("sector_analyses", {})
    sector_data = sector_analyses.get(sector)

    if not sector_data:
        raise HTTPException(status_code=404, detail=f"Sector '{sector}' not found in report")

    return sector_data


def serialize_for_json(obj):
    """Recursively convert datetime objects to ISO strings for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    return obj


def generate_html_report(doc: dict) -> str:
    """Generate a beautifully formatted HTML report."""
    overall = doc.get("overall_analysis", {}) or {}
    sectors = doc.get("sector_analyses", {}) or {}
    metadata = doc.get("analysis_metadata", {}) or {}

    # Sentiment styling
    sentiment = overall.get("sentiment_score", {}) or {}
    score = sentiment.get("score", 3)
    label = sentiment.get("label", "Neutral")
    confidence = sentiment.get("confidence", "medium")

    sentiment_colors = {
        1: ("#dc2626", "#fef2f2", "Strongly Bearish"),
        2: ("#f97316", "#fff7ed", "Bearish"),
        3: ("#eab308", "#fefce8", "Neutral"),
        4: ("#84cc16", "#f7fee7", "Bullish"),
        5: ("#22c55e", "#f0fdf4", "Strongly Bullish")
    }

    sentiment_color, sentiment_bg, _ = sentiment_colors.get(score, sentiment_colors[3])

    confidence_colors = {
        "high": "#22c55e",
        "medium": "#eab308",
        "low": "#dc2626"
    }
    conf_color = confidence_colors.get(confidence, "#eab308")

    # Phase colors
    phase_colors = {
        "A": "#22c55e",
        "B": "#3b82f6",
        "C": "#f59e0b",
        "D": "#ef4444"
    }

    # Sector icons and colors
    sector_info = {
        "core": {"icon": "📊", "color": "#3b82f6"},
        "financial": {"icon": "💰", "color": "#22c55e"},
        "construction": {"icon": "🏗️", "color": "#f59e0b"},
        "manufacturing": {"icon": "🏭", "color": "#8b5cf6"}
    }

    # Build sectors HTML
    sectors_html = ""
    toc_sectors = ""
    for idx, (sector_name, sector_data) in enumerate(sectors.items(), 1):
        if not sector_data:
            continue
        info = sector_info.get(sector_name, {"icon": "📈", "color": "#6b7280"})
        phase = sector_data.get("business_phase", "N/A")
        phase_color = phase_colors.get(phase, "#6b7280")

        # Phase distribution bars
        phase_dist = sector_data.get("phase_distribution", {})
        total_phases = sum(phase_dist.values()) if phase_dist else 1
        phase_bars = ""
        for p in ["A", "B", "C", "D"]:
            count = phase_dist.get(p, 0)
            pct = (count / total_phases * 100) if total_phases > 0 else 0
            phase_bars += f'<div style="flex: {max(pct, 5)}; background: {phase_colors[p]}; height: 24px; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: 600;">{p}: {count}</div>'

        # Key insights
        insights = sector_data.get("key_insights", []) or []
        insights_html = "".join([f'<li style="margin-bottom: 8px; color: #374151;">{insight}</li>' for insight in insights[:5]])

        # Leading indicators
        indicators = sector_data.get("leading_indicators", []) or []
        indicators_html = "".join([f'<span style="display: inline-block; background: #e0e7ff; color: #3730a3; padding: 4px 12px; border-radius: 20px; font-size: 12px; margin: 4px;">{ind}</span>' for ind in indicators[:5]])

        # Source pages
        source_pages = sector_data.get("source_pages", []) or []
        pages_html = ", ".join([f'<span style="color: {info["color"]}; font-weight: 600;">p.{p}</span>' for p in source_pages[:10]])
        if len(source_pages) > 10:
            pages_html += f' <span style="color: #6b7280;">+{len(source_pages) - 10} more</span>'

        toc_sectors += f'<li><a href="#sector-{sector_name}" style="color: {info["color"]}; text-decoration: none;">{info["icon"]} {sector_name.title()} Sector</a></li>'

        sectors_html += f'''
        <div id="sector-{sector_name}" style="background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 24px; overflow: hidden; border-left: 4px solid {info["color"]};">
            <div style="background: linear-gradient(135deg, {info["color"]}15 0%, white 100%); padding: 20px; border-bottom: 1px solid #e5e7eb;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; font-size: 20px; color: #111827;">
                        {info["icon"]} {sector_name.title()} Sector Analysis
                    </h3>
                    <div style="display: flex; gap: 12px; align-items: center;">
                        <span style="background: {phase_color}20; color: {phase_color}; padding: 6px 16px; border-radius: 20px; font-weight: 600; font-size: 13px;">
                            Phase {phase}
                        </span>
                        <span style="background: #f3f4f6; color: #374151; padding: 6px 16px; border-radius: 20px; font-size: 13px;">
                            {sector_data.get("series_count", 0)} Series
                        </span>
                    </div>
                </div>
            </div>

            <div style="padding: 24px;">
                <div style="margin-bottom: 24px;">
                    <h4 style="color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">Summary</h4>
                    <p style="color: #374151; line-height: 1.7; margin: 0; font-size: 15px;">{sector_data.get("summary", "No summary available.")}</p>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px;">
                    <div>
                        <h4 style="color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">Dominant Trend</h4>
                        <p style="color: #111827; font-size: 18px; font-weight: 600; margin: 0; text-transform: capitalize;">{sector_data.get("dominant_trend", "N/A")}</p>
                    </div>
                    <div>
                        <h4 style="color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">Phase Distribution</h4>
                        <div style="display: flex; border-radius: 6px; overflow: hidden;">{phase_bars}</div>
                    </div>
                </div>

                {"<div style='margin-bottom: 24px;'><h4 style='color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;'>Key Insights</h4><ul style='margin: 0; padding-left: 20px;'>" + insights_html + "</ul></div>" if insights else ""}

                {"<div style='margin-bottom: 24px;'><h4 style='color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;'>Leading Indicators</h4><div>" + indicators_html + "</div></div>" if indicators else ""}

                {"<div><h4 style='color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;'>Source Pages</h4><p style='margin: 0;'>" + pages_html + "</p></div>" if source_pages else ""}
            </div>
        </div>
        '''

    # Key themes
    themes = overall.get("key_themes", []) or []
    themes_html = ""
    for theme in themes[:6]:
        if isinstance(theme, dict):
            themes_html += f'''
            <div style="background: #f8fafc; border-radius: 8px; padding: 16px; border-left: 3px solid #3b82f6;">
                <h4 style="margin: 0 0 8px 0; color: #111827; font-size: 15px;">{theme.get("theme_name", "Theme")}</h4>
                <p style="margin: 0; color: #6b7280; font-size: 13px;">{theme.get("description", "")}</p>
            </div>
            '''

    # Recommendations
    recommendations = overall.get("recommendations", []) or []
    recs_html = ""
    for i, rec in enumerate(recommendations[:5], 1):
        recs_html += f'''
        <div style="display: flex; gap: 16px; align-items: flex-start; margin-bottom: 16px;">
            <div style="background: #3b82f6; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px; flex-shrink: 0;">{i}</div>
            <p style="margin: 0; color: #374151; line-height: 1.6; padding-top: 4px;">{rec}</p>
        </div>
        '''

    # Cross-sector trends
    cross_trends = overall.get("cross_sector_trends", {}) or {}
    correlations = cross_trends.get("correlations", []) or []
    correlations_html = ""
    for corr in correlations[:4]:
        if isinstance(corr, dict):
            correlations_html += f'''
            <div style="background: #faf5ff; border-radius: 8px; padding: 12px 16px; border-left: 3px solid #8b5cf6;">
                <strong style="color: #6b21a8;">{corr.get("sectors", ["", ""])[0].title()} ↔ {corr.get("sectors", ["", ""])[1].title()}</strong>
                <span style="color: #7c3aed; margin-left: 8px;">({corr.get("strength", "moderate")})</span>
                <p style="margin: 8px 0 0 0; color: #6b7280; font-size: 13px;">{corr.get("description", "")}</p>
            </div>
            '''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ITR Analysis Report - {doc.get("report_period", "")}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f1f5f9;
            color: #1e293b;
            line-height: 1.6;
        }}
        @media print {{
            body {{ background: white; }}
            .no-print {{ display: none !important; }}
            .page-break {{ page-break-before: always; }}
        }}
    </style>
</head>
<body>
    <div style="max-width: 900px; margin: 0 auto; padding: 40px 20px;">

        <!-- Header -->
        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); border-radius: 16px; padding: 40px; margin-bottom: 32px; color: white;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 32px; font-weight: 700; margin-bottom: 8px;">ITR Economic Analysis Report</h1>
                    <p style="font-size: 18px; opacity: 0.9;">{doc.get("pdf_filename", "Report")}</p>
                    <p style="font-size: 14px; opacity: 0.7; margin-top: 4px;">Period: {doc.get("report_period", "N/A")}</p>
                </div>
                <div style="text-align: right;">
                    <div style="background: rgba(255,255,255,0.2); padding: 16px 24px; border-radius: 12px;">
                        <div style="font-size: 36px; font-weight: 700;">{score}/5</div>
                        <div style="font-size: 14px; opacity: 0.9;">{label}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Table of Contents -->
        <div style="background: white; border-radius: 12px; padding: 24px; margin-bottom: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h2 style="font-size: 18px; color: #111827; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid #e5e7eb;">📑 Table of Contents</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                <ol style="list-style-position: inside; color: #4b5563;">
                    <li><a href="#executive-summary" style="color: #3b82f6; text-decoration: none;">Executive Summary</a></li>
                    <li><a href="#sentiment" style="color: #3b82f6; text-decoration: none;">Sentiment Analysis</a></li>
                    <li><a href="#themes" style="color: #3b82f6; text-decoration: none;">Key Themes</a></li>
                    <li><a href="#recommendations" style="color: #3b82f6; text-decoration: none;">Recommendations</a></li>
                </ol>
                <ol start="5" style="list-style-position: inside; color: #4b5563;">
                    <li><a href="#cross-sector" style="color: #3b82f6; text-decoration: none;">Cross-Sector Trends</a></li>
                    {toc_sectors}
                </ol>
            </div>
        </div>

        <!-- Executive Summary -->
        <div id="executive-summary" style="background: white; border-radius: 12px; padding: 32px; margin-bottom: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h2 style="font-size: 22px; color: #111827; margin-bottom: 20px; display: flex; align-items: center; gap: 12px;">
                <span style="background: #dbeafe; padding: 8px; border-radius: 8px;">📋</span>
                Executive Summary
            </h2>
            <p style="color: #374151; font-size: 16px; line-height: 1.8;">{overall.get("executive_summary", "No executive summary available.")}</p>
        </div>

        <!-- Sentiment Score -->
        <div id="sentiment" style="background: white; border-radius: 12px; overflow: hidden; margin-bottom: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <div style="background: {sentiment_bg}; padding: 32px; border-left: 4px solid {sentiment_color};">
                <h2 style="font-size: 22px; color: #111827; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;">
                    <span style="background: {sentiment_color}20; padding: 8px; border-radius: 8px;">📊</span>
                    Sentiment Analysis
                </h2>
                <div style="display: grid; grid-template-columns: auto 1fr; gap: 32px; align-items: center;">
                    <div style="text-align: center;">
                        <div style="font-size: 64px; font-weight: 700; color: {sentiment_color};">{score}</div>
                        <div style="font-size: 18px; font-weight: 600; color: {sentiment_color};">{label}</div>
                        <div style="margin-top: 8px;">
                            <span style="background: {conf_color}20; color: {conf_color}; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;">
                                {confidence.upper()} CONFIDENCE
                            </span>
                        </div>
                        <div style="display: flex; gap: 6px; justify-content: center; margin-top: 16px;">
                            {"".join([f'<div style="width: 16px; height: 16px; border-radius: 50%; background: {sentiment_colors[i][0] if i <= score else "#e5e7eb"};"></div>' for i in range(1, 6)])}
                        </div>
                    </div>
                    <div>
                        <h4 style="color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">Rationale</h4>
                        <p style="color: #374151; line-height: 1.7; margin: 0;">{sentiment.get("rationale", "No rationale provided.")}</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Key Themes -->
        {"<div id='themes' style='background: white; border-radius: 12px; padding: 32px; margin-bottom: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'><h2 style='font-size: 22px; color: #111827; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;'><span style='background: #fef3c7; padding: 8px; border-radius: 8px;'>💡</span>Key Themes</h2><div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;'>" + themes_html + "</div></div>" if themes else ""}

        <!-- Recommendations -->
        {"<div id='recommendations' style='background: white; border-radius: 12px; padding: 32px; margin-bottom: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'><h2 style='font-size: 22px; color: #111827; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;'><span style='background: #dcfce7; padding: 8px; border-radius: 8px;'>✅</span>Recommendations</h2>" + recs_html + "</div>" if recommendations else ""}

        <!-- Cross-Sector Trends -->
        {"<div id='cross-sector' style='background: white; border-radius: 12px; padding: 32px; margin-bottom: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'><h2 style='font-size: 22px; color: #111827; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;'><span style='background: #f3e8ff; padding: 8px; border-radius: 8px;'>🔗</span>Cross-Sector Correlations</h2><div style='display: grid; gap: 12px;'>" + correlations_html + "</div></div>" if correlations else ""}

        <!-- Sector Analyses -->
        <div class="page-break"></div>
        <h2 style="font-size: 24px; color: #111827; margin-bottom: 24px;">Sector Analysis</h2>
        {sectors_html}

        <!-- Footer -->
        <div style="text-align: center; padding: 32px; color: #6b7280; font-size: 13px; border-top: 1px solid #e5e7eb; margin-top: 40px;">
            <p>Generated by ITR Report Viewer • {metadata.get("generated_at", "")}</p>
            <p style="margin-top: 4px;">Analysis Version: {metadata.get("version", "1.0")} • Model: {metadata.get("llm_model", "N/A")}</p>
        </div>

    </div>
</body>
</html>'''

    return html


@app.get("/api/reports/{report_id}/analysis/export")
async def export_analysis(report_id: str, format: str = "pdf"):
    """Export complete analysis in structured format (PDF, HTML, or JSON)."""
    if format not in ["json", "html", "pdf"]:
        raise HTTPException(status_code=400, detail="Format must be 'pdf', 'html', or 'json'")

    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    if format == "pdf":
        from fastapi.responses import Response
        from weasyprint import HTML, CSS
        import io

        html_content = generate_html_report(doc)

        # Convert HTML to PDF
        pdf_buffer = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)

        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ITR_Analysis_{doc.get('report_period', 'Report').replace(' ', '_')}.pdf"
            }
        )

    if format == "html":
        from fastapi.responses import HTMLResponse
        html_content = generate_html_report(doc)
        return HTMLResponse(
            content=html_content,
            headers={
                "Content-Disposition": f"attachment; filename=analysis_{report_id}.html"
            }
        )

    # JSON format
    export_data = {
        "report_id": doc.get("report_id"),
        "pdf_filename": doc.get("pdf_filename"),
        "report_period": doc.get("report_period"),
        "overall_analysis": doc.get("overall_analysis"),
        "sector_analyses": doc.get("sector_analyses"),
        "analysis_metadata": doc.get("analysis_metadata")
    }

    # Serialize datetime objects to ISO strings
    export_data = serialize_for_json(export_data)

    from fastapi.responses import JSONResponse

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=analysis_{report_id}.json"
        }
    )


@app.post("/api/reports/{report_id}/regenerate-analysis")
async def regenerate_analysis(report_id: str):
    """Regenerate analysis without reprocessing PDF."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        # Create analysis generator
        generator = AnalysisGenerator(llm)

        # Regenerate analysis from existing data
        analysis_result = generator.regenerate_analysis(doc)

        # Update document in database
        coll.update_one(
            {"report_id": report_id},
            {
                "$set": {
                    "overall_analysis": analysis_result.get("overall_analysis"),
                    "sector_analyses": analysis_result.get("sector_analyses"),
                    "analysis_metadata": analysis_result.get("analysis_metadata")
                }
            }
        )

        return {
            "success": True,
            "message": "Analysis regenerated successfully",
            "analysis_metadata": analysis_result.get("analysis_metadata")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")


# ============================================================================
# On-Demand LLM Summary Generation Endpoints
# ============================================================================

class GenerateSummaryRequest(BaseModel):
    """Request model for summary generation."""
    force_regenerate: bool = False


class AnalyzePagesRequest(BaseModel):
    """Request model for custom page analysis."""
    pages: List[int]  # List of page numbers to analyze
    analyst_context: str = ""  # Additional context from the analyst
    prompt_type: str = "general"  # Type of analysis: general, comparison, forecast, risks


@app.post("/api/reports/{report_id}/analyze-pages")
async def analyze_pages_with_llm(report_id: str, request: AnalyzePagesRequest):
    """Analyze selected pages with LLM using extracted text and analyst context."""
    if not AZURE_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    if not request.pages:
        raise HTTPException(status_code=400, detail="No pages selected for analysis")

    # Get the report
    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    # Extract text from selected pages
    document_flow = doc.get("document_flow", [])
    page_contents = []

    for page_num in sorted(request.pages):
        page_data = next((p for p in document_flow if p.get("page_number") == page_num), None)
        if page_data:
            # Get text content from blocks
            blocks = page_data.get("blocks", [])
            text_blocks = [b for b in blocks if b.get("block_type") in ["text", "heading", "paragraph"]]
            text_content = "\n".join(b.get("content", "") for b in text_blocks)

            # Include page summary if available
            page_summary = page_data.get("page_summary", "")
            series_name = page_data.get("series_name", "")

            page_info = f"\n--- Page {page_num}"
            if series_name:
                page_info += f" ({series_name})"
            page_info += " ---\n"

            if page_summary:
                page_info += f"Summary: {page_summary}\n\n"
            if text_content:
                page_info += text_content

            page_contents.append(page_info)

    if not page_contents:
        raise HTTPException(status_code=400, detail="No content found in selected pages")

    combined_text = "\n".join(page_contents)

    # Build prompt based on analysis type
    prompt_templates = {
        "general": "Provide a comprehensive analysis of the following economic report content. Identify key trends, important metrics, and notable insights.",
        "comparison": "Compare and contrast the different series and indicators in this content. Highlight similarities, differences, and relationships between them.",
        "forecast": "Based on the data and trends in this content, provide an outlook and forecast analysis. What are the expected trajectories and key turning points?",
        "risks": "Identify and analyze potential risks and warning signs in this content. What should businesses be cautious about?",
        "opportunities": "Identify opportunities and positive indicators in this content. What sectors or indicators show promise?"
    }

    base_prompt = prompt_templates.get(request.prompt_type, prompt_templates["general"])

    # Build system prompt
    system_prompt = f"""You are an expert economic analyst specializing in ITR Economics reports and business cycle analysis.

{base_prompt}

Important Context:
- ITR Economics uses a 4-phase business cycle: Phase A (Recovery), Phase B (Accelerating Growth), Phase C (Slowing Growth), Phase D (Recession)
- 3/12 rate-of-change indicates momentum direction
- 12/12 rate-of-change shows year-over-year comparison
- Leading indicators predict future economic conditions

Report: {doc.get('pdf_filename', 'Unknown')}
Report Period: {doc.get('report_period', 'Unknown')}
Pages Analyzed: {', '.join(str(p) for p in sorted(request.pages))}

{f"Analyst Notes: {request.analyst_context}" if request.analyst_context else ""}

Provide your analysis in a clear, structured format with:
1. Executive Summary (2-3 sentences)
2. Key Findings (bullet points)
3. Detailed Analysis
4. Implications and Recommendations
"""

    user_prompt = f"Please analyze the following content from the ITR Economics report:\n\n{combined_text[:15000]}"  # Limit context size

    try:
        # Build the full URL
        api_url = f"{AZURE_ENDPOINT}?api-version={AZURE_API_VERSION}"
        print(f"[AI Analysis] Calling API: {api_url[:80]}...")
        print(f"[AI Analysis] Pages: {sorted(request.pages)}, Type: {request.prompt_type}")

        # Call Azure OpenAI (use same endpoint format as Ask AI)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                api_url,
                headers={
                    "Content-Type": "application/json",
                    "api-key": AZURE_API_KEY
                },
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.3
                }
            )

            print(f"[AI Analysis] Response status: {response.status_code}")

            if response.status_code != 200:
                print(f"[AI Analysis] Error response: {response.text[:500]}")
                raise HTTPException(status_code=500, detail=f"AI service error: {response.text}")

            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]

            print(f"[AI Analysis] Success! Response length: {len(ai_response)} chars")

            return {
                "analysis": ai_response,
                "pages_analyzed": sorted(request.pages),
                "prompt_type": request.prompt_type,
                "analyst_context": request.analyst_context,
                "report_id": report_id,
                "timestamp": datetime.now().isoformat()
            }

    except httpx.TimeoutException as e:
        print(f"[AI Analysis] Timeout error: {str(e)}")
        raise HTTPException(status_code=504, detail="AI service timeout - try with fewer pages")
    except httpx.ConnectError as e:
        print(f"[AI Analysis] Connection error: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to AI service: {str(e)}")
    except Exception as e:
        print(f"[AI Analysis] Error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


class SaveAnalysisRequest(BaseModel):
    """Request model for saving analysis to a page."""
    page_number: int
    analysis: str
    analysis_type: str
    pages_analyzed: List[int]
    analyst_context: str = ""
    mode: str = "replace"  # "replace" or "append"


@app.post("/api/reports/{report_id}/save-page-analysis")
async def save_page_analysis(report_id: str, request: SaveAnalysisRequest):
    """Save custom AI analysis to a specific page in the document."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    # Find the page in document_flow
    document_flow = doc.get("document_flow", [])
    page_index = None
    existing_analysis = None

    for i, page in enumerate(document_flow):
        if page.get("page_number") == request.page_number:
            page_index = i
            existing_analysis = page.get("custom_analysis", None)
            break

    if page_index is None:
        raise HTTPException(status_code=404, detail=f"Page {request.page_number} not found")

    # Build the analysis entry
    new_analysis_entry = {
        "content": request.analysis,
        "analysis_type": request.analysis_type,
        "pages_analyzed": request.pages_analyzed,
        "analyst_context": request.analyst_context,
        "timestamp": datetime.now().isoformat()
    }

    # Handle append vs replace
    if request.mode == "append" and existing_analysis:
        # Append to existing analyses list
        if isinstance(existing_analysis, list):
            analyses = existing_analysis + [new_analysis_entry]
        else:
            # Convert old single analysis to list
            analyses = [existing_analysis, new_analysis_entry]
    else:
        # Replace - store as list with single entry
        analyses = [new_analysis_entry]

    # Update the document
    update_path = f"document_flow.{page_index}.custom_analysis"
    coll.update_one(
        {"report_id": report_id},
        {"$set": {update_path: analyses}}
    )

    return {
        "success": True,
        "message": f"Analysis {'appended to' if request.mode == 'append' else 'saved to'} page {request.page_number}",
        "page_number": request.page_number,
        "total_analyses": len(analyses)
    }


@app.get("/api/reports/{report_id}/page/{page_number}/analysis")
async def get_page_analysis(report_id: str, page_number: int):
    """Get custom analysis saved to a specific page."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    # Find the page
    document_flow = doc.get("document_flow", [])
    for page in document_flow:
        if page.get("page_number") == page_number:
            return {
                "page_number": page_number,
                "custom_analysis": page.get("custom_analysis", None),
                "has_analysis": page.get("custom_analysis") is not None
            }

    raise HTTPException(status_code=404, detail=f"Page {page_number} not found")


@app.post("/api/reports/{report_id}/generate-overall-summary")
async def generate_overall_summary(report_id: str, request: GenerateSummaryRequest = None):
    """Generate or regenerate overall LLM summary for the report."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    if llm is None:
        raise HTTPException(status_code=503, detail="LLM service not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    force = request.force_regenerate if request else False

    # Check if overall summary already exists
    existing_overall = doc.get("overall_analysis", {})
    if existing_overall.get("executive_summary") and not force:
        return {
            "success": True,
            "message": "Overall summary already exists",
            "summary": existing_overall.get("executive_summary"),
            "sentiment_score": existing_overall.get("sentiment_score"),
            "regenerated": False
        }

    try:
        generator = AnalysisGenerator(llm)

        # Generate full analysis to get overall summary
        analysis_result = generator.generate_analysis(doc)

        # Update database with new overall analysis
        coll.update_one(
            {"report_id": report_id},
            {
                "$set": {
                    "overall_analysis": analysis_result.get("overall_analysis"),
                    "analysis_metadata": analysis_result.get("analysis_metadata")
                }
            }
        )

        overall = analysis_result.get("overall_analysis", {})
        return {
            "success": True,
            "message": "Overall summary generated successfully",
            "summary": overall.get("executive_summary"),
            "sentiment_score": overall.get("sentiment_score"),
            "key_themes": overall.get("key_themes"),
            "recommendations": overall.get("recommendations"),
            "processing_time": analysis_result.get("analysis_metadata", {}).get("processing_time_seconds"),
            "regenerated": True
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")


@app.post("/api/reports/{report_id}/generate-sector-summary/{sector}")
async def generate_sector_summary(report_id: str, sector: str, request: GenerateSummaryRequest = None):
    """Generate or regenerate LLM summary for a specific sector."""
    valid_sectors = ["core", "financial", "construction", "manufacturing"]
    if sector not in valid_sectors:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sector. Must be one of: {', '.join(valid_sectors)}"
        )

    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    if llm is None:
        raise HTTPException(status_code=503, detail="LLM service not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    force = request.force_regenerate if request else False

    # Check if sector summary already exists
    existing_sectors = doc.get("sector_analyses", {})
    existing_sector = existing_sectors.get(sector, {})
    if existing_sector.get("summary") and not force:
        return {
            "success": True,
            "message": f"Sector '{sector}' summary already exists",
            "sector": sector,
            "summary": existing_sector.get("summary"),
            "dominant_trend": existing_sector.get("dominant_trend"),
            "business_phase": existing_sector.get("business_phase"),
            "regenerated": False
        }

    try:
        generator = AnalysisGenerator(llm)

        # Get page summaries and series by sector
        page_summaries = generator._aggregate_page_summaries(doc)
        series_by_sector = generator._group_series_by_sector(doc)

        # Generate sector analyses
        sector_analyses = generator.generate_sector_analyses(doc, series_by_sector, page_summaries)

        # Convert to dict for storage
        sector_analyses_dict = {}
        for name, analysis in sector_analyses.items():
            sector_analyses_dict[name] = analysis.model_dump() if hasattr(analysis, 'model_dump') else analysis

        # Update database with new sector analyses
        coll.update_one(
            {"report_id": report_id},
            {
                "$set": {
                    "sector_analyses": sector_analyses_dict
                }
            }
        )

        generated_sector = sector_analyses_dict.get(sector, {})
        return {
            "success": True,
            "message": f"Sector '{sector}' summary generated successfully",
            "sector": sector,
            "summary": generated_sector.get("summary"),
            "dominant_trend": generated_sector.get("dominant_trend"),
            "business_phase": generated_sector.get("business_phase"),
            "series_count": generated_sector.get("series_count"),
            "phase_distribution": generated_sector.get("phase_distribution"),
            "key_insights": generated_sector.get("key_insights"),
            "source_pages": generated_sector.get("source_pages"),
            "regenerated": True
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sector summary generation failed: {str(e)}")


@app.post("/api/reports/{report_id}/generate-all-summaries")
async def generate_all_summaries(report_id: str, request: GenerateSummaryRequest = None):
    """Generate all summaries (overall + all sectors) in one request."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    if llm is None:
        raise HTTPException(status_code=503, detail="LLM service not available")

    coll = db["ITRextract_Flow"]
    doc = coll.find_one({"report_id": report_id})

    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        generator = AnalysisGenerator(llm)

        # Generate full analysis
        analysis_result = generator.generate_analysis(doc)

        # Update database
        coll.update_one(
            {"report_id": report_id},
            {
                "$set": {
                    "overall_analysis": analysis_result.get("overall_analysis"),
                    "sector_analyses": analysis_result.get("sector_analyses"),
                    "analysis_metadata": analysis_result.get("analysis_metadata")
                }
            }
        )

        return {
            "success": True,
            "message": "All summaries generated successfully",
            "overall_analysis": analysis_result.get("overall_analysis"),
            "sector_analyses": analysis_result.get("sector_analyses"),
            "analysis_metadata": analysis_result.get("analysis_metadata")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")


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
