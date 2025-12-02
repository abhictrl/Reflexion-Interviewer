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

CRITICAL: Output ONLY the interview question or response. Do NOT include any reasoning, thinking, or meta-commentary. Do NOT explain what you're doing or why. Just ask the question directly.

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
- Ask SPECIFIC follow-up questions based on their LAST response - reference what they just said
- Do NOT repeat questions you've already asked
- Do NOT ask generic questions if you've already asked one
- Encourage detailed explanations by asking for specific examples or details
- Be supportive and professional
- Wrap up gracefully when concluding the interview
- Output ONLY the question/response - no reasoning, no explanations, no meta-commentary

You are currently in Phase {self.current_phase} of the interview. Ask a question appropriate for this phase.

IMPORTANT: 
- Read the candidate's last response carefully
- Ask a SPECIFIC follow-up question that references something they mentioned
- Do NOT repeat any question from the conversation history
- Output ONLY the interview question - no reasoning, no thinking, just the question
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
            
            # If no message generated, create a contextual fallback
            if not next_message:
                next_message = await self._generate_contextual_followup()
            
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
        
        extracted_response = self.nvidia_client.extract_response_text(response)
        
        # If extraction failed or returned None/empty, generate a context-aware question
        if not extracted_response or len(extracted_response.strip()) < 10:
            return await self._generate_contextual_followup()
        
        # Check if this question was already asked
        if self._is_repeated_question(extracted_response):
            logger.warning("Detected repeated question, generating new contextual followup")
            return await self._generate_contextual_followup()
        
        return extracted_response
    
    def _is_repeated_question(self, question: str) -> bool:
        """Check if a question was already asked in the conversation"""
        question_normalized = question.lower().strip()
        
        # Common generic question patterns to detect
        generic_patterns = [
            "tell me more about",
            "can you tell me more",
            "thank you for sharing",
            "can you elaborate",
        ]
        
        # Check against all previous assistant messages
        for msg in self.conversation_history:
            if msg.role == "assistant":
                prev_question = msg.content.lower().strip()
                
                # Check for generic patterns in both questions
                curr_has_generic = any(pattern in question_normalized for pattern in generic_patterns)
                prev_has_generic = any(pattern in prev_question for pattern in generic_patterns)
                
                # If both are generic, they're likely the same
                if curr_has_generic and prev_has_generic:
                    # Check if they're asking about the same thing
                    if "project" in question_normalized and "project" in prev_question:
                        return True
                    if "experience" in question_normalized and "experience" in prev_question:
                        return True
                    if "background" in question_normalized and "background" in prev_question:
                        return True
                
                # Simple similarity check - if questions are very similar, consider it a repeat
                if len(question_normalized) > 20 and len(prev_question) > 20:
                    # Check if they share significant overlap
                    words_curr = set(question_normalized.split())
                    words_prev = set(prev_question.split())
                    if len(words_curr) > 0 and len(words_prev) > 0:
                        overlap = len(words_curr.intersection(words_prev)) / max(len(words_curr), len(words_prev))
                        if overlap > 0.6:  # 60% word overlap suggests repetition (lowered threshold)
                            return True
                
                # Also check for exact or near-exact matches
                if question_normalized == prev_question or question_normalized in prev_question or prev_question in question_normalized:
                    return True
        
        return False
    
    async def _generate_contextual_followup(self) -> str:
        """Generate a context-aware follow-up question based on conversation history"""
        # Get the last user message to create a contextual follow-up
        if self.conversation_history:
            last_user_msg = None
            for msg in reversed(self.conversation_history):
                if msg.role == "user":
                    last_user_msg = msg.content
                    break
            
            if last_user_msg:
                # Generate a contextual follow-up based on what they just said
                # Extract key topics from their response
                key_topics = []
                if "OCR" in last_user_msg or "Optical Character Recognition" in last_user_msg:
                    key_topics.append("OCR integration")
                if "API" in last_user_msg:
                    key_topics.append("API usage")
                if "app" in last_user_msg.lower() or "application" in last_user_msg.lower():
                    key_topics.append("application development")
                
                contextual_prompt = f"""The candidate just said: "{last_user_msg[:200]}"

Generate a SPECIFIC follow-up question that:
- References something specific they mentioned (e.g., OCR, API, app, etc.)
- Asks for technical details or challenges they faced
- Is different from any question already asked
- Stays relevant to Phase {self.current_phase}

Examples of good questions:
- "What challenges did you encounter when integrating the OCR API?"
- "How did you handle error cases in your expense app?"
- "Can you walk me through the data flow in that application?"

Output ONLY the question. No reasoning."""
                
                messages = [
                    {"role": "system", "content": "You are a technical interviewer. Generate SPECIFIC follow-up questions that reference what the candidate just said."},
                    {"role": "user", "content": contextual_prompt}
                ]
                
                response = await self.nvidia_client.chat_completion(
                    messages=messages,
                    model_type="super",
                    temperature=0.8,
                    max_tokens=150
                )
                
                followup = self.nvidia_client.extract_response_text(response)
                if followup and len(followup.strip()) > 10:
                    # Check if this followup is also a repeat
                    if not self._is_repeated_question(followup):
                        return followup.strip()
        
        # Fallback based on phase - make them more specific to avoid repetition
        # Get a hint from conversation history
        recent_topics = []
        for msg in reversed(self.conversation_history[-4:]):
            if msg.role == "user":
                content_lower = msg.content.lower()
                if "python" in content_lower or "java" in content_lower:
                    recent_topics.append("programming languages")
                if "api" in content_lower:
                    recent_topics.append("APIs")
                if "app" in content_lower or "application" in content_lower:
                    recent_topics.append("applications")
                break
        
        topic_hint = recent_topics[0] if recent_topics else "technical skills"
        
        phase_fallbacks = {
            1: f"That's great! Can you walk me through a specific technical challenge you encountered in that project and how you solved it?",
            2: f"Excellent! Can you dive deeper into the technical implementation? What were the key design decisions you made?",
            3: f"Thanks for that detail. Let me ask: what was the most complex problem you had to solve in that project?",
            4: f"Appreciate that insight. How do you approach learning new technologies when starting a project?"
        }
        
        fallback = phase_fallbacks.get(self.current_phase, "That's interesting! Can you tell me more about the technical aspects of that?")
        
        # Make sure this fallback hasn't been used before
        if self._is_repeated_question(fallback):
            # Generate a different variation
            variations = {
                1: "Can you share an example of how you've applied your technical skills in a real-world project?",
                2: "What's a technical problem you've solved that you're particularly proud of?",
                3: "Can you describe a time when you had to debug a complex issue? How did you approach it?",
                4: "What technologies are you most excited to work with, and why?"
            }
            fallback = variations.get(self.current_phase, "Can you elaborate on the technical challenges you faced?")
        
        return fallback
    
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

