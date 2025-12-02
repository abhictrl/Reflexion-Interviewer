"""
NVIDIA NIM API Client

This module provides a wrapper around the NVIDIA NIM API for interacting
with Nemotron models (both the main interview agent and vision-language model).
"""

import httpx
import json
import base64
from typing import Dict, List, Optional, Any, Union
from config.nvidia_config import get_nvidia_config


class NVIDIAClient:
    """Client for interacting with NVIDIA NIM API"""
    
    def __init__(self):
        self.config = get_nvidia_config()
        self.config.validate_config()
        
        # Setup HTTP client
        self.client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model_type: str = "super",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to NVIDIA NIM API
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model_type: Either 'super' (Nemotron-super-49b) or 'vl' (Nemotron-nano-vl)
            temperature: Sampling temperature (uses config default if not provided)
            max_tokens: Maximum tokens to generate (uses config default if not provided)
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            API response as dictionary
        """
        # Select endpoint and model based on type
        if model_type == "super":
            endpoint = self.config.nemotron_super_endpoint
            model = self.config.nemotron_super_model
        elif model_type == "vl":
            endpoint = self.config.nemotron_vl_endpoint
            model = self.config.nemotron_vl_model
        else:
            raise ValueError(f"Invalid model_type: {model_type}. Use 'super' or 'vl'")
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "top_p": self.config.top_p,
            **kwargs
        }
        
        # Make API request with retries
        for attempt in range(self.config.max_retries):
            try:
                # Log request details for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Making NVIDIA API request to: {endpoint}")
                logger.debug(f"Request payload model: {model}")
                logger.debug(f"Request payload keys: {list(payload.keys())}")
                
                response = await self.client.post(endpoint, json=payload)
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPStatusError as e:
                if attempt == self.config.max_retries - 1:
                    # Provide more detailed error information
                    try:
                        error_response = e.response.text[:500] if e.response else "No response body"
                    except:
                        error_response = "Could not read error response"
                    
                    error_detail = f"Status {e.response.status_code}: {error_response}"
                    
                    # Provide helpful suggestions based on status code
                    suggestions = ""
                    if e.response.status_code == 404:
                        suggestions = (
                            "\n\nTroubleshooting 404 error:\n"
                            "1. Verify the endpoint URL is correct for NVIDIA NIM API\n"
                            "2. Check that the model name '{model}' exists and is available\n"
                            "3. Try using: https://ai.api.nvidia.com/v1/chat/completions instead\n"
                            "4. Verify your API key has access to this model\n"
                            "5. Check NVIDIA's documentation for the correct endpoint format"
                        )
                    elif e.response.status_code == 401:
                        suggestions = "\n\nTroubleshooting 401 error: Verify your NVIDIA_API_KEY is correct and has proper permissions"
                    elif e.response.status_code == 403:
                        suggestions = "\n\nTroubleshooting 403 error: Your API key may not have access to this model or endpoint"
                    
                    raise Exception(
                        f"NVIDIA API error after {self.config.max_retries} attempts: {e}\n"
                        f"Endpoint: {endpoint}\n"
                        f"Model: {model}\n"
                        f"Details: {error_detail}{suggestions}"
                    )
                # Wait before retrying (exponential backoff)
                await asyncio.sleep(2 ** attempt)
            
            except Exception as e:
                raise Exception(f"Error calling NVIDIA NIM API: {str(e)}")
    
    async def analyze_resume_image(
        self,
        image_base64: str,
        prompt: str,
        image_format: str = "png"
    ) -> Dict[str, Any]:
        """
        Analyze a resume image using Nemotron-Nano-VL model
        
        Args:
            image_base64: Base64 encoded image data
            prompt: Text prompt for the vision model
            image_format: Image format (png, jpg, jpeg)
        
        Returns:
            API response with extracted resume data
        """
        # Construct multimodal message
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_format};base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
        
        return await self.chat_completion(messages, model_type="vl", max_tokens=4096)
    
    async def generate_interview_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> str:
        """
        Generate an interview response using Nemotron-super-49b
        
        Args:
            system_prompt: System prompt defining the interviewer's behavior
            conversation_history: List of previous messages in the interview
            temperature: Sampling temperature for response generation
        
        Returns:
            Generated response text
        """
        messages = [
            {"role": "system", "content": system_prompt}
        ] + conversation_history
        
        response = await self.chat_completion(
            messages,
            model_type="super",
            temperature=temperature
        )
        
        # Extract the generated text
        return response["choices"][0]["message"]["content"]
    
    def extract_response_text(self, api_response: Dict[str, Any]) -> str:
        """
        Extract the text content from an API response, filtering out reasoning
        
        Args:
            api_response: Raw API response dictionary
        
        Returns:
            Extracted text content with reasoning removed
        """
        try:
            content = api_response["choices"][0]["message"]["content"]
            
            import re
            
            # Quick check: If content starts with obvious reasoning patterns (case-insensitive)
            content_lower = content.strip().lower()
            reasoning_starters = [
                "okay", "the user", "i need to", "i should", "looking at", "given that", 
                "since", "however", "wait,", "alternatively", "but", "considering",
                "given the", "putting it all together"
            ]
            
            # Check if content starts with reasoning
            starts_with_reasoning = any(content_lower.startswith(starter) for starter in reasoning_starters)
            
            # Also check first 50 characters for reasoning patterns
            first_50_lower = content[:50].lower()
            has_reasoning_start = any(starter in first_50_lower for starter in reasoning_starters)
            
            if starts_with_reasoning or has_reasoning_start:
                # Look for actual interview question markers (case-insensitive)
                interview_markers = [
                    r"(?:^|\n)\s*(?:hello|hi|thank you|you|can you|tell me|what|how|why|when|where|let me|i'd like|based on)",
                    r"\*\*A\.I\. Harrison:\*\*",
                    r"A\.I\. Harrison:",
                    r"(?:Could|Would|Can|Will) you",
                ]
                
                found_question = False
                question_text = None
                
                # Try to find actual question in the content - look for questions near the end
                # Questions are usually at the end after all the reasoning
                last_300_chars = content[-300:].strip()
                
                # Look for question patterns in the last 300 characters
                question_patterns = [
                    r'(Could you tell me[^?!.]*\??)',
                    r'(Can you [^?!.]*\??)',
                    r'(Would you [^?!.]*\??)',
                    r'(Tell me [^?!.]*\??)',
                    r'(Looking at [^?!.]*\??)',
                    r'(You have[^?!.]*\??)',
                ]
                
                found_questions = []
                for pattern in question_patterns:
                    matches = re.finditer(pattern, last_300_chars, re.IGNORECASE)
                    for match in matches:
                        q = match.group(1).strip()
                        # Skip if it's reasoning
                        if not any(kw in q.lower() for kw in ['the user', 'the candidate', 'i need to', 'i should']):
                            found_questions.append(q)
                
                if found_questions:
                    # Return the last question found (most likely the actual interview question)
                    question_text = found_questions[-1]
                    # Ensure it ends with question mark if it doesn't already
                    if not question_text.endswith('?'):
                        question_text = question_text.rstrip('.') + '?'
                    return question_text
                
                # If no question found in last 300 chars, return None to let the interview agent handle it
                # Don't return a generic fallback here - let the agent generate a proper question
                return None
            
            # Step 1: Remove reasoning blocks by finding closing tags and taking content after
            reasoning_closing_tags = ["</think>", "</think>", "</reasoning>"]
            for tag in reasoning_closing_tags:
                if tag in content:
                    parts = content.split(tag, 1)
                    if len(parts) > 1:
                        content = parts[1].strip()
                        break
            
            # Step 2: Remove any remaining reasoning tags
            content = content.replace("<think>", "").replace("</think>", "")
            content = content.replace("<reasoning>", "").replace("</reasoning>", "")
            
            # Step 2.5: Detect and remove untagged reasoning blocks
            # Reasoning often starts with phrases like "Okay, the user", "I need to", etc.
            import re
            
            # Check if content starts with reasoning patterns
            reasoning_starters = [
                r'^Okay[,\s]+(?:the user|I\'m|I need to|I should)',
                r'^The user (?:is|has|provided|provided)',
                r'^I need to (?:make sure|ensure|check)',
                r'^(?:Looking|Given|Since|However|Wait,).*?(?:user|candidate|interview)',
            ]
            
            # If content starts with reasoning, try to find actual interview response
            starts_with_reasoning = any(re.match(pattern, content, re.IGNORECASE) for pattern in reasoning_starters)
            
            # Also check if content is very long and contains lots of reasoning keywords
            reasoning_keywords = ['the user', 'the candidate', 'the ai', 'harrison should', 'i need to', 'i should', 
                                 'phase 1', 'the interview', 'the question', 'the response']
            has_excessive_reasoning = len(content) > 500 and sum(1 for kw in reasoning_keywords if kw in content.lower()) >= 3
            
            if starts_with_reasoning or has_excessive_reasoning:
                # Look for actual interview response markers
                response_markers = [
                    r'(?:^|\n)(?:Hello|Hi|Thank you|You|Can you|Tell me|What|How|Why|When|Where|Let me|I\'d like|Based on)',
                    r'\*\*A\.I\. Harrison:\*\*',
                    r'A\.I\. Harrison:',
                ]
                
                found_marker = False
                for marker in response_markers:
                    match = re.search(marker, content, re.IGNORECASE | re.MULTILINE)
                    if match:
                        content = content[match.start():].strip()
                        found_marker = True
                        break
                
                # If no clear marker, try to find first sentence that's TO the candidate
                if not found_marker:
                    sentences = re.split(r'(?<=[.!?])\s+', content)
                    for i, sentence in enumerate(sentences):
                        sentence_lower = sentence.lower()
                        # Skip sentences that are clearly reasoning
                        if any(kw in sentence_lower for kw in reasoning_keywords):
                            continue
                        # Check if sentence is actually addressing the candidate
                        if re.match(r'^(?:Hello|Hi|Thank you|You|Can you|Tell me|What|How|Why)', sentence, re.IGNORECASE):
                            content = ' '.join(sentences[i:]).strip()
                            break
            
            # Step 3: Remove the "A.I. Harrison:" prefix if present
            for prefix in ["**A.I. Harrison:**", "A.I. Harrison:", "**Assistant:**", "Assistant:"]:
                if prefix in content:
                    idx = content.find(prefix)
                    content = content[idx + len(prefix):].strip()
                    break
            
            # Step 4: Remove parenthetical explanations (e.g., "*(This question...)*")
            import re
            # Remove inline patterns like "*(This question transitions smoothly...)*"
            # This matches asterisk-wrapped parenthetical explanations (handles multiline)
            content = re.sub(r'\s*\*\([^)]+\)\*', '', content, flags=re.DOTALL)
            # Also match patterns where asterisks might be on separate lines or formatted differently
            content = re.sub(r'\*\s*\([^)]+\)\s*\*', '', content, flags=re.DOTALL)
            # Remove parentheticals that explain the question/response
            content = re.sub(r'\s*\([^)]*(?:This question|This maintains|aligns|invites|transitions|probes|which are critical)[^)]*\)', '', content, flags=re.IGNORECASE)
            # Remove any remaining asterisk-only explanations
            content = re.sub(r'\s*\*[^*]*(?:question|maintains|aligns|invites|transitions)[^*]*\*\s*', '', content, flags=re.IGNORECASE)
            
            # Step 5: Clean up notes and separators, and remove explanatory lines
            lines = []
            for line in content.split("\n"):
                line_clean = line.strip()
                # Skip empty lines, separators, and note markers
                if not line_clean or line_clean.startswith(("---", "Note:", "*Note:", "**Note:")):
                    continue
                # Skip lines that are entirely explanatory parentheticals
                if re.match(r'^[\*\s]*\([^)]*(?:This|question|maintains|aligns|invites|transitions|probes)[^)]*\)[\*\s]*$', line_clean, re.IGNORECASE):
                    continue
                # Remove inline parenthetical explanations from each line
                line_clean = re.sub(r'\s*\*\([^)]*\)\*\s*', '', line_clean)
                line_clean = re.sub(r'\s*\([^)]*(?:This|question|maintains|aligns)[^)]*\)\s*', '', line_clean, flags=re.IGNORECASE)
                if line_clean.strip():
                    lines.append(line_clean)
            
            content = "\n".join(lines).strip()
            
            # Step 6: Final cleanup - remove trailing parenthetical explanations
            content = re.sub(r'\s*\*\([^)]+\)\*\s*$', '', content)
            content = re.sub(r'\s*\([^)]*(?:This|question|maintains)[^)]*\)\s*$', '', content, flags=re.IGNORECASE)
            
            # Step 7: Final check - if content is still mostly reasoning, try harder to extract question
            if content:
                reasoning_keywords = ['the user', 'the candidate', 'the ai', 'harrison should', 'i need to', 
                                     'i should', 'phase 1', 'the interview', 'the question', 'the response',
                                     'wait,', 'looking', 'given', 'however', 'since', 'alternatively',
                                     'considering', 'but since', 'putting it all together']
                reasoning_count = sum(1 for kw in reasoning_keywords if kw in content.lower())
                word_count = len(content.split())
                
                # If content is long and has lots of reasoning keywords, try to extract just the question
                if word_count > 100 and reasoning_count > 3:
                    # Strategy 1: Look for the last complete question in the text
                    # Questions usually come after all the reasoning
                    question_patterns = [
                        r'(Could you tell me[^?!.]*\?)',
                        r'(Can you [^?!.]*\?)',
                        r'(Would you [^?!.]*\?)',
                        r'(Tell me [^?!.]*\?)',
                        r'(What [^?!.]*\?)',
                        r'(How [^?!.]*\?)',
                        r'(Why [^?!.]*\?)',
                        r'(Looking at [^?!.]*\?)',
                        r'(You have[^?!.]*\?)',
                    ]
                    
                    all_questions = []
                    for pattern in question_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            question = match.group(1).strip()
                            # Skip if it's clearly reasoning
                            if not any(kw in question.lower() for kw in reasoning_keywords[:8]):
                                all_questions.append((match.start(), question))
                    
                    # Return the last question found (most likely the actual interview question)
                    if all_questions:
                        # Sort by position and get the last one
                        all_questions.sort(key=lambda x: x[0])
                        return all_questions[-1][1]
                    
                    # Strategy 2: Find the last sentence ending with a question mark
                    sentences = re.split(r'([.!?]\s+)', content)
                    for i in range(len(sentences) - 1, -1, -1):
                        if i > 0 and '?' in sentences[i-1]:
                            potential_question = (sentences[i-1] + sentences[i]).strip()
                            sentence_lower = potential_question.lower()
                            # Check if it's not reasoning
                            if not any(kw in sentence_lower for kw in reasoning_keywords[:10]):
                                # Check if it's actually asking something
                                if any(word in sentence_lower for word in ['you', 'tell', 'what', 'how', 'why', 'could', 'can', 'would']):
                                    return potential_question
                    
                    # Strategy 3: Look for question-like patterns near the end (even if incomplete)
                    last_200_chars = content[-200:].strip()
                    # Find sentences that start with question words
                    question_starters = r'\b(Could|Can|Would|Tell me|What|How|Why|You have|Looking at)'
                    matches = list(re.finditer(question_starters, last_200_chars, re.IGNORECASE))
                    if matches:
                        # Take the text from the last question starter to the end
                        last_match = matches[-1]
                        potential_question = last_200_chars[last_match.start():].strip()
                        # Clean it up - take first complete sentence or reasonable chunk
                        if '?' in potential_question:
                            potential_question = potential_question.split('?')[0] + '?'
                        elif len(potential_question) > 150:
                            # Take first 150 chars or until a period
                            potential_question = potential_question[:150].rsplit('.', 1)[0] + '.'
                        if not any(kw in potential_question.lower() for kw in reasoning_keywords[:5]):
                            return potential_question
                    
                    # Last resort: return None to let interview agent generate contextual followup
                    return None
            
            return content if content else None
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to extract response text: {str(e)}")


# Import asyncio for sleep function
import asyncio

