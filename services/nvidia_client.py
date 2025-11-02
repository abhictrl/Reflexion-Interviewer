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
                response = await self.client.post(endpoint, json=payload)
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPStatusError as e:
                if attempt == self.config.max_retries - 1:
                    raise Exception(f"NVIDIA API error after {self.config.max_retries} attempts: {e}")
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
        Extract the text content from an API response
        
        Args:
            api_response: Raw API response dictionary
        
        Returns:
            Extracted text content
        """
        try:
            return api_response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to extract response text: {str(e)}")


# Import asyncio for sleep function
import asyncio

