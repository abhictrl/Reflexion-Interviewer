"""
Pydantic Data Models for API validation

This module defines all the data schemas used throughout the application
for request/response validation and type safety.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# Resume & Candidate Models
# ============================================

class ResumeSkills(BaseModel):
    """Skills extracted from resume"""
    languages: List[str] = Field(default_factory=list, description="Programming languages")
    frameworks: List[str] = Field(default_factory=list, description="Frameworks and libraries")
    tools: List[str] = Field(default_factory=list, description="Development tools")
    databases: List[str] = Field(default_factory=list, description="Databases")
    cloud_platforms: List[str] = Field(default_factory=list, description="Cloud platforms")


class WorkExperience(BaseModel):
    """Work experience entry"""
    company: str = Field(description="Company name")
    position: str = Field(description="Job title/position")
    duration: str = Field(description="Duration of employment")
    description: str = Field(description="Job description/responsibilities")


class Education(BaseModel):
    """Education entry"""
    institution: str = Field(description="School/university name")
    degree: str = Field(description="Degree obtained")
    field: Optional[str] = Field(None, description="Field of study")
    graduation_year: Optional[str] = Field(None, description="Graduation year")


class Project(BaseModel):
    """Project entry from resume"""
    name: str = Field(description="Project name")
    description: str = Field(description="Project description")
    technologies: List[str] = Field(default_factory=list, description="Technologies used")


class CandidateProfile(BaseModel):
    """Complete candidate profile extracted from resume"""
    name: str = Field(description="Candidate name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    summary: Optional[str] = Field(None, description="Professional summary")
    skills: ResumeSkills = Field(description="Technical skills")
    experience: List[WorkExperience] = Field(default_factory=list, description="Work experience")
    education: List[Education] = Field(default_factory=list, description="Education")
    projects: List[Project] = Field(default_factory=list, description="Projects")
    years_of_experience: Optional[int] = Field(None, description="Total years of experience")


# ============================================
# Interview State Models
# ============================================

class InterviewPhase(BaseModel):
    """Interview phase information"""
    phase_number: int = Field(ge=1, le=4, description="Phase number (1-4)")
    name: str = Field(description="Phase name")
    description: str = Field(description="Phase description")
    question_count: int = Field(default=0, description="Number of questions asked")
    max_questions: int = Field(default=5, description="Maximum questions per phase")


class InterviewMessage(BaseModel):
    """Single message in the interview conversation"""
    role: Literal["system", "assistant", "user"] = Field(description="Message role")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")


class InterviewState(BaseModel):
    """Current state of an interview session"""
    session_id: str = Field(description="Unique session identifier")
    candidate_profile: CandidateProfile = Field(description="Candidate information")
    job_description: str = Field(description="Job description text")
    current_phase: int = Field(ge=1, le=4, description="Current interview phase (1-4)")
    total_questions: int = Field(default=0, description="Total questions asked")
    conversation_history: List[InterviewMessage] = Field(
        default_factory=list,
        description="Conversation history"
    )
    started_at: datetime = Field(default_factory=datetime.now, description="Interview start time")
    status: Literal["active", "completed", "paused"] = Field(
        default="active",
        description="Interview status"
    )


# ============================================
# Assessment Models
# ============================================

class PhaseScore(BaseModel):
    """Score for a specific interview phase"""
    phase_number: int = Field(ge=1, le=4, description="Phase number")
    phase_name: str = Field(description="Phase name")
    technical_accuracy: float = Field(ge=0, le=10, description="Technical accuracy score (0-10)")
    problem_solving: float = Field(ge=0, le=10, description="Problem-solving score (0-10)")
    communication: float = Field(ge=0, le=10, description="Communication score (0-10)")
    depth_of_knowledge: float = Field(ge=0, le=10, description="Knowledge depth score (0-10)")
    average_score: float = Field(description="Average of all scores")


class CandidateStrengths(BaseModel):
    """Identified strengths of the candidate"""
    top_strengths: List[str] = Field(description="Main strengths")
    demonstrated_skills: List[str] = Field(description="Skills demonstrated in interview")
    notable_achievements: List[str] = Field(default_factory=list, description="Notable achievements")


class CandidateWeaknesses(BaseModel):
    """Identified weaknesses or areas for improvement"""
    areas_for_improvement: List[str] = Field(description="Areas needing development")
    missing_skills: List[str] = Field(default_factory=list, description="Expected but not demonstrated skills")
    concerns: List[str] = Field(default_factory=list, description="Red flags or concerns")


class InterviewReport(BaseModel):
    """Final assessment report"""
    session_id: str = Field(description="Interview session ID")
    candidate_name: str = Field(description="Candidate name")
    job_title: str = Field(description="Job position applied for")
    overall_score: float = Field(ge=0, le=10, description="Overall assessment score (0-10)")
    recommendation: Literal["strong_yes", "yes", "maybe", "no", "strong_no"] = Field(
        description="Hiring recommendation"
    )
    phase_scores: List[PhaseScore] = Field(description="Breakdown by interview phase")
    strengths: CandidateStrengths = Field(description="Candidate strengths")
    weaknesses: CandidateWeaknesses = Field(description="Areas for improvement")
    summary: str = Field(description="Overall assessment summary")
    key_highlights: List[str] = Field(description="Key highlights from the interview")
    generated_at: datetime = Field(default_factory=datetime.now, description="Report generation time")
    raw_analysis: Optional[Dict[str, Any]] = Field(None, description="Raw analysis data")


# ============================================
# API Request/Response Models
# ============================================

class ResumeUploadRequest(BaseModel):
    """Request to upload resume and job description"""
    job_description: str = Field(description="Job description text")


class ResumeUploadResponse(BaseModel):
    """Response after resume upload"""
    session_id: str = Field(description="Interview session ID")
    candidate_profile: CandidateProfile = Field(description="Extracted candidate information")
    message: str = Field(description="Status message")


class InterviewMessageRequest(BaseModel):
    """Request to send a message in the interview"""
    session_id: str = Field(description="Interview session ID")
    message: str = Field(description="Candidate's response or question")


class InterviewMessageResponse(BaseModel):
    """Response from the interview agent"""
    session_id: str = Field(description="Interview session ID")
    message: str = Field(description="Agent's response/question")
    current_phase: int = Field(ge=1, le=4, description="Current interview phase")
    phase_name: str = Field(description="Phase name")
    total_questions: int = Field(description="Total questions asked so far")
    interview_complete: bool = Field(default=False, description="Whether interview is complete")


class InterviewStatusResponse(BaseModel):
    """Response for interview status check"""
    session_id: str = Field(description="Interview session ID")
    status: str = Field(description="Interview status")
    current_phase: int = Field(ge=1, le=4, description="Current phase")
    total_questions: int = Field(description="Total questions asked")
    conversation_length: int = Field(description="Number of messages in conversation")
    started_at: datetime = Field(description="Interview start time")


class InterviewReportResponse(BaseModel):
    """Response containing the assessment report"""
    report: InterviewReport = Field(description="Complete assessment report")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    session_id: Optional[str] = Field(None, description="Associated session ID if applicable")

