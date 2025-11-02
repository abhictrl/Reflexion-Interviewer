"""
Assessment & Scoring Engine

This module generates structured assessment reports based on interview responses.
It analyzes conversation quality, depth, and technical accuracy to provide
objective hiring recommendations.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from services.nvidia_client import NVIDIAClient
from models.schemas import (
    InterviewState,
    InterviewReport,
    PhaseScore,
    CandidateStrengths,
    CandidateWeaknesses
)


logger = logging.getLogger(__name__)


class AssessmentEngine:
    """Service for generating interview assessment reports"""
    
    def __init__(self):
        self.nvidia_client = NVIDIAClient()
        self.assessment_prompt_template = """You are an expert hiring manager analyzing a technical interview transcript.

Analyze the candidate's responses throughout the interview and provide a comprehensive assessment.

Interview Context:
- Job Description: {job_description}
- Candidate: {candidate_name}
- Phase Breakdown:
{phase_breakdown}

Interview Transcript (last {message_count} messages):
{transcript}

Provide your assessment as JSON with this structure:
{{
    "overall_score": <float 0-10>,
    "recommendation": "strong_yes" | "yes" | "maybe" | "no" | "strong_no",
    "phase_scores": [
        {{
            "phase_number": 1,
            "phase_name": "Warm-up & Background",
            "technical_accuracy": <float 0-10>,
            "problem_solving": <float 0-10>,
            "communication": <float 0-10>,
            "depth_of_knowledge": <float 0-10>
        }},
        {{... for each phase}}
    ],
    "strengths": {{
        "top_strengths": ["strength1", "strength2", ...],
        "demonstrated_skills": ["skill1", "skill2", ...],
        "notable_achievements": ["achievement1", ...]
    }},
    "weaknesses": {{
        "areas_for_improvement": ["area1", "area2", ...],
        "missing_skills": ["skill1", ...],
        "concerns": ["concern1", ...]
    }},
    "summary": "Overall assessment summary paragraph",
    "key_highlights": ["highlight1", "highlight2", ...]
}}

Focus on:
- Technical accuracy and depth of knowledge
- Problem-solving approach and reasoning
- Communication clarity and articulation
- Alignment with job requirements
- Demonstrated skills vs. listed skills"""
    
    async def generate_report(
        self,
        interview_state: InterviewState,
        candidate_skills: List[str]
    ) -> InterviewReport:
        """
        Generate a comprehensive assessment report
        
        Args:
            interview_state: Current interview state with conversation history
            candidate_skills: List of skills from the resume
        
        Returns:
            Complete interview assessment report
        """
        try:
            logger.info(f"Generating assessment for session {interview_state.session_id}")
            
            # Build assessment prompt
            assessment_prompt = self._build_assessment_prompt(interview_state)
            
            # Get AI assessment
            messages = [
                {"role": "system", "content": "You are an expert technical interviewer and hiring manager."},
                {"role": "user", "content": assessment_prompt}
            ]
            
            response = await self.nvidia_client.chat_completion(
                messages=messages,
                model_type="super",
                temperature=0.3  # Lower temperature for more consistent scoring
            )
            
            # Parse the assessment
            assessment_data = self._parse_assessment_response(response)
            
            # Create the report
            report = InterviewReport(
                session_id=interview_state.session_id,
                candidate_name=interview_state.candidate_profile.name,
                job_title=self._extract_job_title(interview_state.job_description),
                overall_score=assessment_data["overall_score"],
                recommendation=assessment_data["recommendation"],
                phase_scores=self._parse_phase_scores(assessment_data.get("phase_scores", [])),
                strengths=CandidateStrengths(**assessment_data["strengths"]),
                weaknesses=CandidateWeaknesses(**assessment_data["weaknesses"]),
                summary=assessment_data["summary"],
                key_highlights=assessment_data["key_highlights"],
                raw_analysis=assessment_data
            )
            
            logger.info(f"Assessment complete. Overall score: {report.overall_score}/10")
            return report
        
        except Exception as e:
            logger.error(f"Error generating assessment: {str(e)}")
            # Return a fallback report
            return self._generate_fallback_report(interview_state)
    
    def _build_assessment_prompt(self, interview_state: InterviewState) -> str:
        """Build the assessment prompt from interview state"""
        # Extract recent conversation
        recent_messages = interview_state.conversation_history[-20:]
        transcript = "\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in recent_messages
        ])
        
        # Build phase breakdown
        phase_breakdown = "\n".join([
            f"- Phase {i+1}: {phase.name} - {phase.description}"
            for i, phase in enumerate(InterviewAgent.PHASES)
        ])
        
        return self.assessment_prompt_template.format(
            job_description=interview_state.job_description[:500],
            candidate_name=interview_state.candidate_profile.name,
            phase_breakdown=phase_breakdown,
            message_count=len(recent_messages),
            transcript=transcript[:3000]  # Limit transcript length
        )
    
    def _parse_assessment_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the AI assessment response"""
        import json
        
        response_text = self.nvidia_client.extract_response_text(response)
        
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            assessment_data = json.loads(response_text)
            return assessment_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse assessment JSON: {e}")
            logger.error(f"Response: {response_text[:500]}")
            raise ValueError("Failed to parse assessment response")
    
    def _parse_phase_scores(self, phase_data: List[Dict[str, Any]]) -> List[PhaseScore]:
        """Parse phase scores into PhaseScore objects"""
        phase_scores = []
        for phase in phase_data:
            score = PhaseScore(
                phase_number=phase["phase_number"],
                phase_name=phase["phase_name"],
                technical_accuracy=float(phase["technical_accuracy"]),
                problem_solving=float(phase["problem_solving"]),
                communication=float(phase["communication"]),
                depth_of_knowledge=float(phase["depth_of_knowledge"]),
                average_score=(
                    float(phase["technical_accuracy"]) +
                    float(phase["problem_solving"]) +
                    float(phase["communication"]) +
                    float(phase["depth_of_knowledge"])
                ) / 4.0
            )
            phase_scores.append(score)
        
        return phase_scores
    
    def _extract_job_title(self, job_description: str) -> str:
        """Extract job title from job description"""
        # Simple extraction - look for common patterns
        lines = job_description.split('\n')
        if lines:
            first_line = lines[0].strip()
            if len(first_line) < 100 and any(keyword in first_line.lower() for keyword in 
                ['engineer', 'developer', 'software', 'architect', 'scientist']):
                return first_line
        return "Software Engineer"
    
    def _generate_fallback_report(self, interview_state: InterviewState) -> InterviewReport:
        """Generate a fallback report if AI assessment fails"""
        logger.warning("Using fallback assessment report")
        
        return InterviewReport(
            session_id=interview_state.session_id,
            candidate_name=interview_state.candidate_profile.name,
            job_title=self._extract_job_title(interview_state.job_description),
            overall_score=5.0,
            recommendation="maybe",
            phase_scores=[
                PhaseScore(
                    phase_number=i+1,
                    phase_name=phase.name,
                    technical_accuracy=5.0,
                    problem_solving=5.0,
                    communication=5.0,
                    depth_of_knowledge=5.0,
                    average_score=5.0
                )
                for i, phase in enumerate(InterviewAgent.PHASES)
            ],
            strengths=CandidateStrengths(
                top_strengths=["Completed interview successfully"],
                demonstrated_skills=[],
                notable_achievements=[]
            ),
            weaknesses=CandidateWeaknesses(
                areas_for_improvement=["Assessment incomplete"],
                missing_skills=[],
                concerns=["AI assessment generation failed"]
            ),
            summary="Assessment report generation encountered an error. Manual review recommended.",
            key_highlights=["Interview session completed"]
        )
    
    async def close(self):
        """Clean up resources"""
        await self.nvidia_client.close()


# Import InterviewAgent for PHASES reference
from services.interview_agent import InterviewAgent

