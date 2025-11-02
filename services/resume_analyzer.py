"""
Resume Analysis Service

This module handles PDF resume processing and analysis using the Nemotron-Nano-12B-v2-VL
vision-language model. It converts PDFs to images and extracts structured candidate
information.
"""

import base64
import io
import logging
from typing import Dict, Any, Optional
from PIL import Image
import pdfplumber
from pdf2image import convert_from_bytes
from services.nvidia_client import NVIDIAClient
from models.schemas import CandidateProfile, ResumeSkills, WorkExperience, Education, Project


logger = logging.getLogger(__name__)


class ResumeAnalyzer:
    """Service for analyzing resumes using vision-language AI"""
    
    def __init__(self):
        self.nvidia_client = NVIDIAClient()
        self.resume_analysis_prompt = """You are an expert resume parser. Analyze this resume and extract structured information in JSON format.

Return ONLY a JSON object with the following structure:
{
    "name": "Candidate's full name",
    "email": "Email address if available",
    "phone": "Phone number if available",
    "summary": "Professional summary or objective if present",
    "years_of_experience": <number> or null,
    "skills": {
        "languages": ["Python", "Java", ...],
        "frameworks": ["React", "Django", ...],
        "tools": ["Git", "Docker", ...],
        "databases": ["PostgreSQL", "MongoDB", ...],
        "cloud_platforms": ["AWS", "Azure", ...]
    },
    "experience": [
        {
            "company": "Company name",
            "position": "Job title",
            "duration": "Start date - End date",
            "description": "Key responsibilities and achievements"
        }
    ],
    "education": [
        {
            "institution": "School/University name",
            "degree": "Degree type",
            "field": "Field of study",
            "graduation_year": "YYYY" or null
        }
    ],
    "projects": [
        {
            "name": "Project name",
            "description": "Project description",
            "technologies": ["tech1", "tech2", ...]
        }
    ]
}

Be thorough and extract all relevant technical information. If a field is not available, use null or an empty list.
Focus on technical skills, programming languages, frameworks, and experience relevant to software engineering."""
    
    async def analyze_pdf(self, pdf_bytes: bytes) -> CandidateProfile:
        """
        Analyze a PDF resume and extract structured information
        
        Args:
            pdf_bytes: Binary content of the PDF file
        
        Returns:
            CandidateProfile object with extracted information
        """
        try:
            # Convert PDF to images
            logger.info("Converting PDF to images...")
            images = convert_from_bytes(pdf_bytes, dpi=200, fmt='PNG')
            
            if not images:
                raise ValueError("Failed to convert PDF to images")
            
            # Analyze the first page (you could extend to multiple pages)
            logger.info(f"Analyzing {len(images)} page(s) of resume...")
            candidate_data = await self._analyze_resume_image(images[0])
            
            # Parse and validate the extracted data
            profile = self._parse_candidate_data(candidate_data)
            logger.info(f"Successfully extracted profile for: {profile.name}")
            
            return profile
            
        except Exception as e:
            logger.error(f"Error analyzing resume: {str(e)}")
            raise
    
    async def _analyze_resume_image(self, image: Image.Image) -> Dict[str, Any]:
        """
        Analyze a single resume image using the vision-language model
        
        Args:
            image: PIL Image object
        
        Returns:
            Extracted candidate data as dictionary
        """
        # Convert image to base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Call NVIDIA VL model
        response = await self.nvidia_client.analyze_resume_image(
            image_base64=image_base64,
            prompt=self.resume_analysis_prompt,
            image_format="png"
        )
        
        # Extract the JSON response
        response_text = self.nvidia_client.extract_response_text(response)
        
        # Try to parse JSON from the response
        import json
        try:
            # Sometimes the model wraps JSON in markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            candidate_data = json.loads(response_text)
            return candidate_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            raise ValueError("Failed to parse structured data from AI response")
    
    def _parse_candidate_data(self, data: Dict[str, Any]) -> CandidateProfile:
        """
        Parse raw extracted data into a CandidateProfile object
        
        Args:
            data: Raw dictionary from AI response
        
        Returns:
            Validated CandidateProfile object
        """
        try:
            # Parse skills
            skills_data = data.get("skills", {})
            skills = ResumeSkills(
                languages=skills_data.get("languages", []),
                frameworks=skills_data.get("frameworks", []),
                tools=skills_data.get("tools", []),
                databases=skills_data.get("databases", []),
                cloud_platforms=skills_data.get("cloud_platforms", [])
            )
            
            # Parse experience
            experience = [
                WorkExperience(
                    company=exp.get("company", ""),
                    position=exp.get("position", ""),
                    duration=exp.get("duration", ""),
                    description=exp.get("description", "")
                )
                for exp in data.get("experience", [])
            ]
            
            # Parse education
            education = [
                Education(
                    institution=edu.get("institution", ""),
                    degree=edu.get("degree", ""),
                    field=edu.get("field"),
                    graduation_year=edu.get("graduation_year")
                )
                for edu in data.get("education", [])
            ]
            
            # Parse projects
            projects = [
                Project(
                    name=proj.get("name", ""),
                    description=proj.get("description", ""),
                    technologies=proj.get("technologies", [])
                )
                for proj in data.get("projects", [])
            ]
            
            # Create profile
            profile = CandidateProfile(
                name=data.get("name", "Unknown Candidate"),
                email=data.get("email"),
                phone=data.get("phone"),
                summary=data.get("summary"),
                skills=skills,
                experience=experience,
                education=education,
                projects=projects,
                years_of_experience=data.get("years_of_experience")
            )
            
            return profile
        
        except Exception as e:
            logger.error(f"Error parsing candidate data: {str(e)}")
            raise ValueError(f"Failed to create candidate profile: {str(e)}")
    
    async def close(self):
        """Clean up resources"""
        await self.nvidia_client.close()


# Note: pdf2image requires poppler-utils to be installed on the system
# For macOS: brew install poppler
# For Ubuntu: sudo apt-get install poppler-utils

