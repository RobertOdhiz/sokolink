"""
WhatsApp webhook handlers for receiving and processing messages.
"""
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, status, Depends, BackgroundTasks
from fastapi.responses import PlainTextResponse
import structlog

from models.webhook_models import WhatsAppWebhook, WebhookVerification, SessionData
from services.whatsapp_service import whatsapp_service
from services.watsonx_service import watsonx_service
from services.database_service import db_service
from utils.security import verify_webhook_signature, sanitize_phone_number, validate_business_input
from utils.formatters import format_business_type_suggestion

logger = structlog.get_logger()
router = APIRouter(prefix="/webhook", tags=["whatsapp"])


@router.get("/whatsapp")
async def verify_webhook(request: Request) -> str:
    """
    Verify WhatsApp webhook during initial setup.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Challenge string for verification
    """
    try:
        # Get query parameters
        hub_mode = request.query_params.get("hub.mode")
        hub_challenge = request.query_params.get("hub.challenge")
        hub_verify_token = request.query_params.get("hub.verify_token")
        
        # Validate verification request
        verification = WebhookVerification(
            hub_mode=hub_mode,
            hub_challenge=hub_challenge,
            hub_verify_token=hub_verify_token
        )
        
        # Check verify token
        from config import get_settings
        settings = get_settings()
        
        if verification.hub_verify_token != settings.whatsapp_webhook_verify_token:
            logger.warning("Invalid webhook verify token", 
                          provided_token=verification.hub_verify_token)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid verify token"
            )
        
        logger.info("Webhook verification successful")
        return hub_challenge
        
    except Exception as e:
        logger.error("Webhook verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook verification failed"
        )


@router.post("/whatsapp")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    Receive WhatsApp webhook messages.
    
    Args:
        request: FastAPI request object
        background_tasks: Background tasks for async processing
        
    Returns:
        Dict: Acknowledgment response
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify webhook signature
        signature = request.headers.get("X-Hub-Signature-256", "")
        from config import get_settings
        settings = get_settings()
        
        if not verify_webhook_signature(body, signature, settings.whatsapp_webhook_verify_token):
            logger.warning("Invalid webhook signature")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid signature"
            )
        
        # Parse webhook payload
        webhook_data = await request.json()
        webhook = WhatsAppWebhook(**webhook_data)
        
        # Process webhook in background
        background_tasks.add_task(process_webhook_messages, webhook)
        
        logger.info("Webhook received and queued for processing", 
                   entries=len(webhook.entry))
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error("Error processing webhook", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def process_webhook_messages(webhook: WhatsAppWebhook) -> None:
    """
    Process webhook messages asynchronously.
    
    Args:
        webhook: WhatsApp webhook data
    """
    try:
        for entry in webhook.entry:
            for change in entry.changes:
                if change.field == "messages":
                    await process_messages(change.value)
                elif change.field == "message_status":
                    await process_message_status(change.value)
                    
    except Exception as e:
        logger.error("Error processing webhook messages", error=str(e))


async def process_messages(value: Any) -> None:
    """
    Process incoming messages.
    
    Args:
        value: WhatsApp webhook value
    """
    try:
        if not value.messages:
            return
        
        for message in value.messages:
            await process_single_message(message, value.metadata)
            
    except Exception as e:
        logger.error("Error processing messages", error=str(e))


async def process_single_message(message: Any, metadata: Dict[str, str]) -> None:
    """
    Process single incoming message.
    
    Args:
        message: WhatsApp message
        metadata: Message metadata
    """
    try:
        phone_number = sanitize_phone_number(message.from_)
        message_content = ""
        
        # Extract message content based on type
        if message.text:
            message_content = message.text.body
        elif message.interactive:
            if message.interactive.button_reply:
                message_content = message.interactive.button_reply.get("title", "")
            elif message.interactive.list_reply:
                message_content = message.interactive.list_reply.get("title", "")
        
        if not message_content:
            logger.warning("Empty message content", phone_number=phone_number)
            return
        
        # Log incoming message
        db_service.log_conversation(
            session_id="",  # Will be set when we get/create session
            phone_number=phone_number,
            message_type="incoming",
            message_content=message_content,
            metadata={
                "message_id": message.id,
                "timestamp": message.timestamp,
                "message_type": message.type
            }
        )
        
        # Get or create session
        session = await get_or_create_session(phone_number)
        
        # Process user message
        await process_user_message(session, message_content, message.id)
        
    except Exception as e:
        logger.error("Error processing single message", error=str(e))


async def get_or_create_session(phone_number: str) -> SessionData:
    """
    Get existing session or create new one.
    
    Args:
        phone_number: User's phone number
        
    Returns:
        SessionData: User session
    """
    try:
        # Try to get existing active session
        session = db_service.get_active_session_by_phone(phone_number)
        
        if not session:
            # Create new session
            session_id = db_service.create_session(phone_number, {
                "phone_number": phone_number,
                "created_at": datetime.utcnow().isoformat(),
                "message_count": 0
            })
            session = db_service.get_session(session_id)
        
        return session
        
    except Exception as e:
        logger.error("Error getting/creating session", error=str(e), phone_number=phone_number)
        raise


async def process_user_message(session: SessionData, message_content: str, message_id: str) -> None:
    """
    Process user message and generate response.
    
    Args:
        session: User session
        message_content: User's message
        message_id: WhatsApp message ID
    """
    try:
        # Validate and sanitize input
        validation_result = validate_business_input(message_content)
        sanitized_message = validation_result["sanitized_input"]
        
        # Handle special commands
        if sanitized_message.upper() in ["HELP", "🆘"]:
            await whatsapp_service.send_help_message(session.phone_number)
            return
        
        if sanitized_message.upper() in ["START", "RESTART"]:
            # Create new session
            new_session_id = db_service.create_session(session.phone_number, {
                "phone_number": session.phone_number,
                "restarted": True
            })
            await whatsapp_service.send_welcome_message(session.phone_number)
            return
        
        # Update session context
        context = session.context.copy()
        context.update({
            "last_message": sanitized_message,
            "message_count": session.message_count + 1,
            "last_activity": datetime.utcnow().isoformat()
        })
        
        # Try to extract business information
        business_info = extract_business_info(sanitized_message)
        context.update(business_info)
        
        # Update session
        db_service.update_session(session.session_id, context)
        
        # Generate compliance response using Watsonx
        try:
            compliance_response = await watsonx_service.execute_compliance_workflow(
                sanitized_message, context
            )
            
            # Save compliance response
            db_service.save_compliance_response(
                session.session_id, 
                session.phone_number, 
                compliance_response
            )
            
            # Send response to user
            await whatsapp_service.send_compliance_response(
                session.phone_number, 
                compliance_response
            )
            
            # Log outgoing message
            db_service.log_conversation(
                session_id=session.session_id,
                phone_number=session.phone_number,
                message_type="outgoing",
                message_content="Compliance guidance sent",
                metadata={
                    "response_type": "compliance_guidance",
                    "total_cost": compliance_response.total_estimated_cost,
                    "total_timeline": compliance_response.total_timeline_days
                }
            )
            
        except Exception as e:
            logger.error("Error generating compliance response", error=str(e))
            
            # Send error message
            await whatsapp_service.send_error_message(
                session.phone_number,
                "COMPLIANCE_ERROR",
                "I'm having trouble processing your request. Please try again with more specific details about your business."
            )
        
    except Exception as e:
        logger.error("Error processing user message", error=str(e))
        
        # Send generic error message
        try:
            await whatsapp_service.send_error_message(
                session.phone_number,
                "PROCESSING_ERROR",
                "Something went wrong. Please try again."
            )
        except:
            pass  # Don't fail if we can't send error message


def extract_business_info(message: str) -> Dict[str, Any]:
    """
    Extract business information from user message.
    
    Args:
        message: User's message
        
    Returns:
        Dict: Extracted business information
    """
    business_info = {}
    
    # Simple keyword-based extraction (in production, use NLP)
    message_lower = message.lower()
    
    # Business types
    business_types = {
        "restaurant": ["restaurant", "food", "cafe", "hotel", "catering"],
        "retail": ["shop", "store", "retail", "selling", "merchandise"],
        "salon": ["salon", "beauty", "hair", "spa", "barber"],
        "construction": ["construction", "building", "contractor", "renovation"],
        "transport": ["transport", "logistics", "delivery", "truck", "taxi"],
        "manufacturing": ["manufacturing", "production", "factory", "processing"],
        "services": ["services", "consulting", "professional", "agency"]
    }
    
    for business_type, keywords in business_types.items():
        if any(keyword in message_lower for keyword in keywords):
            business_info["business_type"] = business_type
            break
    
    # Business scale
    if any(word in message_lower for word in ["small", "micro", "tiny"]):
        business_info["business_scale"] = "small"
    elif any(word in message_lower for word in ["medium", "mid"]):
        business_info["business_scale"] = "medium"
    elif any(word in message_lower for word in ["large", "big", "major"]):
        business_info["business_scale"] = "large"
    else:
        business_info["business_scale"] = "small"  # Default
    
    # Location (simple extraction)
    kenyan_counties = [
        "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", "malindi",
        "kitale", "garissa", "kakamega", "kisii", "meru", "nyeri", "machakos"
    ]
    
    for county in kenyan_counties:
        if county in message_lower:
            business_info["location"] = county.title()
            break
    
    return business_info


async def process_message_status(value: Any) -> None:
    """
    Process message status updates.
    
    Args:
        value: WhatsApp webhook value
    """
    try:
        if not value.statuses:
            return
        
        for status in value.statuses:
            logger.info("Message status update", 
                       message_id=status.id,
                       status=status.status,
                       recipient_id=status.recipient_id)
            
            # You can implement additional logic here for status tracking
            # For example, update database with delivery status
            
    except Exception as e:
        logger.error("Error processing message status", error=str(e))
