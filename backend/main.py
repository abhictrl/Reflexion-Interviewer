"""
FastAPI Backend Application

Main entry point for the Reflexion Interviewer backend API.
Handles resume upload, interview management, and report generation.
"""

import os
import sys
import logging
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.resume_analyzer import ResumeAnalyzer
from services.interview_agent import InterviewAgent
from services.assessment_engine import AssessmentEngine
from models.schemas import (
    ResumeUploadRequest,
    ResumeUploadResponse,
    InterviewMessageRequest,
    InterviewMessageResponse,
    InterviewStatusResponse,
    InterviewReportResponse,
    ErrorResponse
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# In-memory session storage (use Redis in production)
active_sessions: dict[str, InterviewAgent] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Reflexion Interviewer backend...")
    yield
    logger.info("Shutting down Reflexion Interviewer backend...")
    # Cleanup code here if needed


# Initialize FastAPI app
app = FastAPI(
    title="Reflexion Interviewer API",
    description="AI-powered autonomous interview agent for technical screenings",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# ============================================
# Resume Upload Endpoint
# ============================================

@app.post("/api/upload-resume", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    job_description: str = None
):
    """
    Upload a resume PDF and job description to start an interview
    
    Expected:
    - Multipart form with 'file' (PDF) and 'job_description' (text)
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Read file content
        file_content = await file.read()
        logger.info(f"Uploaded resume: {file.filename} ({len(file_content)} bytes)")
        
        # Validate job description
        if not job_description:
            raise HTTPException(status_code=400, detail="Job description is required")
        
        # Analyze resume
        analyzer = ResumeAnalyzer()
        try:
            candidate_profile = await analyzer.analyze_pdf(file_content)
            logger.info(f"Resume analyzed for: {candidate_profile.name}")
        except Exception as e:
            logger.error(f"Error analyzing resume: {str(e)}", exc_info=True)
            # Provide more specific error messages
            error_message = str(e)
            if "poppler" in error_message.lower() or "pdftoppm" in error_message.lower():
                raise HTTPException(
                    status_code=500,
                    detail="PDF processing error. Please ensure poppler-utils is installed. On macOS: brew install poppler"
                )
            elif "NVIDIA_API_KEY" in error_message or "API key" in error_message:
                raise HTTPException(
                    status_code=500,
                    detail="NVIDIA API key not configured. Please set NVIDIA_API_KEY in .env file"
                )
            elif "timeout" in error_message.lower():
                raise HTTPException(
                    status_code=500,
                    detail="Request to NVIDIA API timed out. Please try again."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process resume: {error_message}"
                )
        finally:
            await analyzer.close()
        
        # Initialize interview agent
        agent = InterviewAgent(candidate_profile, job_description)
        session_id = agent.session_id
        
        # Store session
        active_sessions[session_id] = agent
        
        logger.info(f"Interview session created: {session_id}")
        
        return ResumeUploadResponse(
            session_id=session_id,
            candidate_profile=candidate_profile,
            message="Resume uploaded and interview session created successfully"
        )
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading resume: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process resume")


# ============================================
# Interview Management Endpoints
# ============================================

@app.post("/api/interview/message", response_model=InterviewMessageResponse)
async def send_interview_message(request: InterviewMessageRequest):
    """
    Send a message to the interview agent and receive a response
    
    This handles both candidate responses and generates the next question
    """
    try:
        # Get session
        agent = active_sessions.get(request.session_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        # Process message
        response_text = await agent.process_candidate_response(request.message)
        
        # Get current state
        state = agent.get_interview_state()
        
        # Determine phase name
        phase_name = InterviewAgent.PHASES[state.current_phase - 1].name
        
        # Check if complete
        interview_complete = state.status == "completed"
        
        # Cleanup completed sessions after a delay (in production, move to background task)
        if interview_complete:
            logger.info(f"Interview {request.session_id} completed")
        
        return InterviewMessageResponse(
            session_id=request.session_id,
            message=response_text or "Interview completed",
            current_phase=state.current_phase,
            phase_name=phase_name,
            total_questions=state.total_questions,
            interview_complete=interview_complete
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing interview message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process message")


@app.get("/api/interview/status/{session_id}", response_model=InterviewStatusResponse)
async def get_interview_status(session_id: str):
    """Get the current status of an interview session"""
    try:
        agent = active_sessions.get(session_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        state = agent.get_interview_state()
        
        return InterviewStatusResponse(
            session_id=session_id,
            status=state.status,
            current_phase=state.current_phase,
            total_questions=state.total_questions,
            conversation_length=len(state.conversation_history),
            started_at=state.started_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting interview status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get status")


# ============================================
# Report Generation Endpoint
# ============================================

@app.get("/api/interview/report/{session_id}", response_model=InterviewReportResponse)
async def generate_interview_report(session_id: str):
    """Generate the final assessment report for an interview"""
    try:
        agent = active_sessions.get(session_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        # Get interview state
        state = agent.get_interview_state()
        
        # Generate report
        assessment_engine = AssessmentEngine()
        try:
            candidate_skills = []
            if state.candidate_profile.skills:
                candidate_skills = state.candidate_profile.skills.languages + \
                                 state.candidate_profile.skills.frameworks
            
            report = await assessment_engine.generate_report(state, candidate_skills)
            logger.info(f"Report generated for session {session_id}")
        finally:
            await assessment_engine.close()
        
        return InterviewReportResponse(report=report)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


# ============================================
# Health Check
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "service": "Reflexion Interviewer API"
    }


@app.get("/")
async def root():
    """Serve the frontend interface"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {
        "message": "Reflexion Interviewer API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# For debugging - get all active sessions (remove in production)
@app.get("/debug/sessions")
async def get_all_sessions():
    """Debug endpoint to list all active sessions"""
    return {
        "session_count": len(active_sessions),
        "session_ids": list(active_sessions.keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

