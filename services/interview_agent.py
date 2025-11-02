"""
Interview Agent Service (A.I. Harrison)

This module implements the core interview agent that manages the multi-phase
interview process, state management, and orchestrates the conversation flow.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.nvidia_client import NVIDIAClient
from models.schemas import (
    CandidateProfile,
    InterviewState,
    InterviewMessage,
    InterviewPhase
)


logger = logging.getLogger(__name__)


class InterviewAgent:
    """
    Main interview agent that orchestrates the multi-phase interview process
    
    The agent (A.I. Harrison) manages:
    - Phase transitions (4 phases total)
    - Question generation and follow-ups
    - Conversation history
    - Interview state
    """
    
    # Phase definitions
    PHASES = [
        InterviewPhase(
            phase_number=1,
            name="Warm-up & Background",
            description="Getting to know the candidate and their background",
            max_questions=3
        ),
        InterviewPhase(
            phase_number=2,
            name="Technical Depth",
            description="Deep dive into technical skills from the resume",
            max_questions=6
        ),
        InterviewPhase(
            phase_number=3,
            name="Problem-Solving Scenario",
            description="Real-world problem-solving and system design",
            max_questions=4
        ),
        InterviewPhase(
            phase_number=4,
            name="Behavioral & Wrap-up",
            description="Soft skills, behavioral questions, and conclusion",
            max_questions=3
        )
    ]
    
    def __init__(self, candidate_profile: CandidateProfile, job_description: str):
        """
        Initialize the interview agent
        
        Args:
            candidate_profile: Extracted candidate information
            job_description: Job description text
        """
        self.candidate_profile = candidate_profile
        self.job_description = job_description
        self.nvidia_client = NVIDIAClient()
        
        # Create new session
        self.session_id = str(uuid.uuid4())
        self.current_phase = 1
        self.questions_asked_in_phase = 0
        self.total_questions = 0
        self.conversation_history: List[InterviewMessage] = []
        self.started_at = datetime.now()
        self.status = "active"
        
        # Initialize system prompt
        self._build_system_prompt()
        
        # Track scores for each phase (used by assessment engine)
        self.phase_scores = {}
        
        logger.info(f"Initialized interview session {self.session_id} for {candidate_profile.name}")
    
    def _build_system_prompt(self):
        """Build the system prompt for A.I. Harrison"""
        self.system_prompt = f"""You are A.I. Harrison, a professional and friendly senior software engineering interviewer conducting a technical interview.

Your role:
- Conduct a thorough but respectful technical interview
- Ask probing questions based on the candidate's resume
- Adapt your questions based on their answers
- Maintain a professional yet conversational tone
- Provide constructive feedback when appropriate

Candidate Information:
Name: {self.candidate_profile.name}
Experience: {self.candidate_profile.years_of_experience or 'Not specified'} years
Skills: {', '.join(self._get_all_skills())}

Job Description:
{self.job_description[:1000]}

Interview Structure:
- Phase 1: Warm-up & Background (get to know the candidate)
- Phase 2: Technical Depth (deep dive into resume skills)
- Phase 3: Problem-Solving (scenarios and system design)
- Phase 4: Behavioral & Wrap-up (soft skills and conclusion)

Guidelines:
- Keep questions relevant to the job and candidate's background
- Ask follow-up questions based on their answers
- Encourage detailed explanations
- Be supportive and professional
- Wrap up gracefully when concluding the interview

Important: You are currently in Phase {self.current_phase} of the interview. Stay focused on the current phase's objectives.
"""
    
    def _get_all_skills(self) -> List[str]:
        """Get all skills from the candidate profile"""
        skills = []
        if self.candidate_profile.skills:
            skills.extend(self.candidate_profile.skills.languages)
            skills.extend(self.candidate_profile.skills.frameworks)
            skills.extend(self.candidate_profile.skills.tools)
            skills.extend(self.candidate_profile.skills.databases)
            skills.extend(self.candidate_profile.skills.cloud_platforms)
        return skills
    
    async def generate_opening(self) -> str:
        """
        Generate the opening message for the interview
        
        Returns:
            Opening message text
        """
        opening_messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "assistant",
                "content": f"""Hello {self.candidate_profile.name}! I'm A.I. Harrison, and I'll be conducting your technical interview today.

I've reviewed your resume and I'm excited to learn more about your experience with {', '.join(self._get_all_skills()[:5])}.

Let's start with a warm-up question: Tell me a bit about yourself and your background in software engineering. What drew you to this field?"""
            }
        ]
        
        response = await self.nvidia_client.chat_completion(
            messages=opening_messages,
            model_type="super",
            temperature=0.8
        )
        
        opening = self.nvidia_client.extract_response_text(response)
        
        # Record the opening message
        self.conversation_history.append(
            InterviewMessage(role="assistant", content=opening)
        )
        
        return opening
    
    async def process_candidate_response(self, candidate_message: str) -> Optional[str]:
        """
        Process a candidate's response and generate the next question or conclusion
        
        Args:
            candidate_message: Candidate's response text
        
        Returns:
            Next question or None if interview is complete
        """
        try:
            # Add candidate message to history
            self.conversation_history.append(
                InterviewMessage(role="user", content=candidate_message)
            )
            
            # Check if we should move to the next phase
            if self._should_advance_phase():
                if self.current_phase < 4:
                    self.current_phase += 1
                    self.questions_asked_in_phase = 0
                    self._build_system_prompt()  # Update system prompt for new phase
                    logger.info(f"Advancing to Phase {self.current_phase}")
                else:
                    # Interview complete
                    self.status = "completed"
                    return await self._generate_closing()
            
            # Generate next response based on current phase
            next_message = await self._generate_next_message()
            
            if next_message:
                self.questions_asked_in_phase += 1
                self.total_questions += 1
                self.conversation_history.append(
                    InterviewMessage(role="assistant", content=next_message)
                )
            
            return next_message
        
        except Exception as e:
            logger.error(f"Error processing candidate response: {str(e)}")
            raise
    
    async def _generate_next_message(self) -> Optional[str]:
        """Generate the next message/question for the candidate"""
        # Build conversation messages
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add recent conversation history (last 10 messages to manage context)
        recent_history = self.conversation_history[-10:]
        for msg in recent_history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Get response from NVIDIA model
        response = await self.nvidia_client.chat_completion(
            messages=messages,
            model_type="super",
            temperature=0.8
        )
        
        return self.nvidia_client.extract_response_text(response)
    
    def _should_advance_phase(self) -> bool:
        """Determine if we should advance to the next phase"""
        current_phase_def = self.PHASES[self.current_phase - 1]
        return self.questions_asked_in_phase >= current_phase_def.max_questions
    
    async def _generate_closing(self) -> str:
        """Generate the closing message for the interview"""
        closing = """Thank you for taking the time to interview with us today! You've provided great insights into your technical background and problem-solving approach.

The interview process is now complete. We'll review your responses and be in touch soon. Do you have any questions for me about the position or the team?"""
        
        self.conversation_history.append(
            InterviewMessage(role="assistant", content=closing)
        )
        
        return closing
    
    def get_interview_state(self) -> InterviewState:
        """Get the current state of the interview"""
        current_phase_def = self.PHASES[self.current_phase - 1]
        
        return InterviewState(
            session_id=self.session_id,
            candidate_profile=self.candidate_profile,
            job_description=self.job_description,
            current_phase=self.current_phase,
            total_questions=self.total_questions,
            conversation_history=self.conversation_history,
            started_at=self.started_at,
            status=self.status
        )
    
    async def close(self):
        """Clean up resources"""
        await self.nvidia_client.close()

