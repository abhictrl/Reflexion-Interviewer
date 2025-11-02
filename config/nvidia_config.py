"""
NVIDIA NIM API Configuration

This module contains configuration for accessing NVIDIA's Nemotron models
via the NIM (NVIDIA Inference Microservices) API endpoints.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class NVIDIAConfig(BaseSettings):
    """Configuration for NVIDIA NIM API access"""
    
    # API Authentication - BaseSettings will automatically read from NVIDIA_API_KEY env var
    api_key: str = Field(
        default="",
        validation_alias="NVIDIA_API_KEY"
    )
    
    # Model Endpoints
    nemotron_super_endpoint: str = Field(
        default="https://integrate.api.nvidia.com/v1/chat/completions",
        validation_alias="NEMOTRON_SUPER_49B_ENDPOINT"
    )
    nemotron_vl_endpoint: str = Field(
        default="https://integrate.api.nvidia.com/v1/chat/completions",
        validation_alias="NEMOTRON_NANO_VL_ENDPOINT"
    )
    
    # Model Names
    nemotron_super_model: str = Field(
        default="nvidia/nemotron-super-49b-v1_5",
        validation_alias="NEMOTRON_SUPER_49B_MODEL"
    )
    nemotron_vl_model: str = Field(
        default="nvidia/nemotron-nano-12b-v2-vl",
        validation_alias="NEMOTRON_NANO_VL_MODEL"
    )
    
    # API Configuration
    timeout: int = 60  # seconds
    max_retries: int = 3
    
    # Model Parameters
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env that we don't use
        populate_by_name=True  # Allow both field name and alias
    )
    
    def validate_config(self) -> bool:
        """Validate that required configuration is present"""
        if not self.api_key or self.api_key == "your_nvidia_api_key_here":
            raise ValueError("NVIDIA_API_KEY is required but not set. Please set it in .env file")
        return True


# Global configuration instance
nvidia_config = NVIDIAConfig()


def get_nvidia_config() -> NVIDIAConfig:
    """Get the NVIDIA configuration instance"""
    return nvidia_config

