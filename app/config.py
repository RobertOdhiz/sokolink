"""
Configuration management for Sokolink Advisor application.
"""
import os
from typing import Optional
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Configuration
    app_name: str = "Sokolink Advisor"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Database Configuration
    database_url: str = "sqlite:///./sokolink_advisor.db"
    
    # WhatsApp Business API Configuration
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_webhook_verify_token: str
    whatsapp_api_version: str = "v18.0"
    
    # IBM Watsonx Orchestrate Configuration
    watsonx_api_key: str
    watsonx_base_url: str = "https://api.watsonx.orchestrate.ibm.com"
    watsonx_workflow_id: str = "sokolink_compliance_advisor"
    watsonx_project_id: str
    
    # Security Configuration
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Rate Limiting
    rate_limit_per_minute: int = 10
    rate_limit_burst: int = 20
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    @validator('database_url')
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v:
            raise ValueError("Database URL is required")
        return v
    
    @validator('whatsapp_access_token')
    def validate_whatsapp_token(cls, v):
        """Validate WhatsApp access token."""
        if not v:
            raise ValueError("WhatsApp access token is required")
        return v
    
    @validator('watsonx_api_key')
    def validate_watsonx_key(cls, v):
        """Validate Watsonx API key."""
        if not v:
            raise ValueError("Watsonx API key is required")
        return v
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        """Validate secret key."""
        if not v or len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings