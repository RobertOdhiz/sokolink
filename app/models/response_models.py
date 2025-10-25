"""
Pydantic models for API response structures.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class ComplianceStepType(str, Enum):
    """Types of compliance steps."""
    PERMIT = "permit"
    LICENSE = "license"
    REGISTRATION = "registration"
    TAX = "tax"
    INSURANCE = "insurance"
    OTHER = "other"


class AuthorityType(str, Enum):
    """Types of regulatory authorities."""
    COUNTY_GOVERNMENT = "county_government"
    NATIONAL_GOVERNMENT = "national_government"
    KRA = "kra"
    NEMA = "nema"
    KEBS = "kebs"
    OTHER = "other"


class ComplianceStep(BaseModel):
    """Individual compliance step structure."""
    step_number: int = Field(..., ge=1, description="Step sequence number")
    title: str = Field(..., min_length=1, description="Step title")
    description: str = Field(..., min_length=1, description="Detailed step description")
    cost: int = Field(..., ge=0, description="Estimated cost in KES")
    timeline_days: int = Field(..., ge=1, description="Estimated timeline in days")
    authority: str = Field(..., description="Responsible authority")
    authority_type: AuthorityType = Field(..., description="Type of authority")
    documents_required: List[str] = Field(default_factory=list, description="Required documents")
    contact_info: Optional[str] = Field(None, description="Authority contact information")
    website: Optional[str] = Field(None, description="Authority website")
    location: Optional[str] = Field(None, description="Physical location")
    step_type: ComplianceStepType = Field(..., description="Type of compliance step")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisite steps")
    estimated_processing_time: Optional[str] = Field(None, description="Processing time estimate")
    
    @validator('documents_required')
    def validate_documents(cls, v):
        """Validate documents list."""
        if not isinstance(v, list):
            raise ValueError("Documents must be a list")
        return [doc.strip() for doc in v if doc.strip()]
    
    @validator('prerequisites')
    def validate_prerequisites(cls, v):
        """Validate prerequisites list."""
        if not isinstance(v, list):
            raise ValueError("Prerequisites must be a list")
        return [prereq.strip() for prereq in v if prereq.strip()]


class ComplianceResponse(BaseModel):
    """Main compliance guidance response structure."""
    success: bool = Field(..., description="Response success status")
    session_id: str = Field(..., description="Session identifier")
    compliance_steps: List[ComplianceStep] = Field(..., description="List of compliance steps")
    total_estimated_cost: int = Field(..., ge=0, description="Total estimated cost in KES")
    total_timeline_days: int = Field(..., ge=1, description="Total estimated timeline in days")
    business_type: Optional[str] = Field(None, description="Identified business type")
    business_scale: Optional[str] = Field(None, description="Business scale (small, medium, large)")
    location: Optional[str] = Field(None, description="Business location")
    additional_notes: Optional[str] = Field(None, description="Additional guidance notes")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Response generation timestamp")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="AI confidence score")
    
    @validator('compliance_steps')
    def validate_steps(cls, v):
        """Validate compliance steps."""
        if not v:
            raise ValueError("At least one compliance step is required")
        
        # Check for duplicate step numbers
        step_numbers = [step.step_number for step in v]
        if len(step_numbers) != len(set(step_numbers)):
            raise ValueError("Step numbers must be unique")
        
        # Validate step sequence
        sorted_steps = sorted(v, key=lambda x: x.step_number)
        for i, step in enumerate(sorted_steps):
            if step.step_number != i + 1:
                raise ValueError("Step numbers must be sequential starting from 1")
        
        return sorted_steps
    
    @validator('total_estimated_cost')
    def validate_total_cost(cls, v, values):
        """Validate total cost matches sum of step costs."""
        if 'compliance_steps' in values:
            calculated_total = sum(step.cost for step in values['compliance_steps'])
            if v != calculated_total:
                raise ValueError("Total cost must match sum of individual step costs")
        return v
    
    @validator('total_timeline_days')
    def validate_total_timeline(cls, v, values):
        """Validate total timeline is reasonable."""
        if 'compliance_steps' in values:
            max_step_timeline = max(step.timeline_days for step in values['compliance_steps'])
            if v < max_step_timeline:
                raise ValueError("Total timeline must be at least as long as the longest individual step")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Error response structure."""
    success: bool = Field(False, description="Response success status")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthCheckResponse(BaseModel):
    """Health check response structure."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    services: Dict[str, str] = Field(..., description="External service statuses")
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MetricsResponse(BaseModel):
    """Metrics response structure."""
    total_sessions: int = Field(..., description="Total number of sessions")
    active_sessions: int = Field(..., description="Currently active sessions")
    total_messages: int = Field(..., description="Total messages processed")
    successful_responses: int = Field(..., description="Successful compliance responses")
    failed_responses: int = Field(..., description="Failed compliance responses")
    average_response_time: float = Field(..., description="Average response time in seconds")
    watsonx_api_calls: int = Field(..., description="Total Watsonx API calls")
    whatsapp_messages_sent: int = Field(..., description="Total WhatsApp messages sent")
    error_rate: float = Field(..., description="Error rate percentage")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WhatsAppMessageRequest(BaseModel):
    """WhatsApp message sending request structure."""
    to: str = Field(..., description="Recipient phone number")
    message: str = Field(..., min_length=1, description="Message content")
    message_type: str = Field(default="text", description="Message type")
    template_name: Optional[str] = Field(None, description="Template name for template messages")
    template_params: Optional[List[str]] = Field(None, description="Template parameters")
    interactive_components: Optional[Dict[str, Any]] = Field(None, description="Interactive message components")
    
    @validator('to')
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        # Remove any non-digit characters
        digits_only = ''.join(filter(str.isdigit, v))
        if len(digits_only) < 10:
            raise ValueError("Invalid phone number format")
        return v
