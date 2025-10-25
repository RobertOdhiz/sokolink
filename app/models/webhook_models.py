"""
Pydantic models for WhatsApp webhook data structures.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class WhatsAppContact(BaseModel):
    """WhatsApp contact information."""
    profile: Optional[Dict[str, str]] = None
    wa_id: str = Field(..., description="WhatsApp ID of the contact")


class WhatsAppContext(BaseModel):
    """WhatsApp message context."""
    from_: str = Field(..., alias="from", description="Sender's WhatsApp ID")
    id: str = Field(..., description="Message ID")


class WhatsAppText(BaseModel):
    """WhatsApp text message content."""
    body: str = Field(..., description="Message text content")


class WhatsAppInteractive(BaseModel):
    """WhatsApp interactive message content."""
    type: str = Field(..., description="Interactive message type")
    button_reply: Optional[Dict[str, str]] = None
    list_reply: Optional[Dict[str, str]] = None


class WhatsAppMessage(BaseModel):
    """WhatsApp message structure."""
    from_: str = Field(..., alias="from", description="Sender's WhatsApp ID")
    id: str = Field(..., description="Message ID")
    timestamp: str = Field(..., description="Message timestamp")
    type: str = Field(..., description="Message type (text, interactive, etc.)")
    text: Optional[WhatsAppText] = None
    interactive: Optional[WhatsAppInteractive] = None
    context: Optional[WhatsAppContext] = None


class WhatsAppValue(BaseModel):
    """WhatsApp webhook value structure."""
    messaging_product: str = Field(..., description="Messaging product type")
    metadata: Dict[str, str] = Field(..., description="Message metadata")
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessage]] = None
    statuses: Optional[List[Dict[str, Any]]] = None


class WhatsAppChange(BaseModel):
    """WhatsApp webhook change structure."""
    value: WhatsAppValue = Field(..., description="Change value")
    field: str = Field(..., description="Changed field")


class WhatsAppEntry(BaseModel):
    """WhatsApp webhook entry structure."""
    id: str = Field(..., description="Entry ID")
    changes: List[WhatsAppChange] = Field(..., description="List of changes")


class WhatsAppWebhook(BaseModel):
    """WhatsApp webhook payload structure."""
    object: str = Field(..., description="Webhook object type")
    entry: List[WhatsAppEntry] = Field(..., description="List of entries")
    
    @validator('object')
    def validate_object(cls, v):
        """Validate webhook object type."""
        if v != "whatsapp_business_account":
            raise ValueError("Invalid webhook object type")
        return v


class WebhookVerification(BaseModel):
    """WhatsApp webhook verification request."""
    hub_mode: str = Field(..., alias="hub.mode")
    hub_challenge: str = Field(..., alias="hub.challenge")
    hub_verify_token: str = Field(..., alias="hub.verify_token")
    
    @validator('hub_mode')
    def validate_hub_mode(cls, v):
        """Validate hub mode."""
        if v != "subscribe":
            raise ValueError("Invalid hub mode")
        return v


class MessageStatus(BaseModel):
    """WhatsApp message status update."""
    id: str = Field(..., description="Message ID")
    status: str = Field(..., description="Message status")
    timestamp: str = Field(..., description="Status timestamp")
    recipient_id: str = Field(..., description="Recipient WhatsApp ID")
    conversation: Optional[Dict[str, Any]] = None
    pricing: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None


class SessionData(BaseModel):
    """User session data structure."""
    session_id: str = Field(..., description="Unique session identifier")
    phone_number: str = Field(..., description="User's phone number")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    conversation_state: str = Field(default="active", description="Current conversation state")
    context: Dict[str, Any] = Field(default_factory=dict, description="Session context data")
    message_count: int = Field(default=0, description="Number of messages in session")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
