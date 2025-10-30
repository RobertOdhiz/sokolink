"""
REST API endpoints for Sokolink Advisor.
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from models.response_models import (
    ComplianceResponse, ErrorResponse, HealthCheckResponse, 
    MetricsResponse, WhatsAppMessageRequest
)
from services.whatsapp_service import whatsapp_service
from services.watsonx_service import watsonx_service
from services.database_service import db_service
from utils.security import verify_token, validate_environment
from app.config import get_settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["api"])
security = HTTPBearer()
settings = get_settings()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token
        
    Returns:
        Dict: User information
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint for monitoring.
    
    Returns:
        HealthCheckResponse: Service health status
    """
    try:
        # Check external services
        whatsapp_health = await whatsapp_service.health_check()
        watsonx_health = await watsonx_service.health_check()
        
        services = {
            "whatsapp": whatsapp_health["status"],
            "watsonx": watsonx_health["status"],
            "database": "healthy"  # Assume healthy if no exception
        }
        
        # Calculate uptime (simplified)
        uptime_seconds = 0  # In production, track actual uptime
        
        return HealthCheckResponse(
            status="healthy" if all(s == "healthy" for s in services.values()) else "degraded",
            version=settings.app_version,
            environment=settings.environment,
            services=services,
            uptime_seconds=uptime_seconds
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthCheckResponse(
            status="unhealthy",
            version=settings.app_version,
            environment=settings.environment,
            services={"error": str(e)},
            uptime_seconds=0
        )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(current_user: Dict[str, Any] = Depends(get_current_user)) -> MetricsResponse:
    """
    Get application metrics.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        MetricsResponse: Application metrics
    """
    try:
        # In production, these would come from actual metrics collection
        metrics = MetricsResponse(
            total_sessions=0,
            active_sessions=0,
            total_messages=0,
            successful_responses=0,
            failed_responses=0,
            average_response_time=0.0,
            watsonx_api_calls=0,
            whatsapp_messages_sent=0,
            error_rate=0.0
        )
        
        logger.info("Metrics requested", user=current_user.get("sub"))
        return metrics
        
    except Exception as e:
        logger.error("Error getting metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )


@router.post("/compliance/query", response_model=ComplianceResponse)
async def query_compliance(
    query: str,
    phone_number: str,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ComplianceResponse:
    """
    Query compliance requirements for a business.
    
    Args:
        query: Business query
        phone_number: User's phone number
        background_tasks: Background tasks
        current_user: Authenticated user
        
    Returns:
        ComplianceResponse: Compliance guidance
    """
    try:
        # Validate input
        if not query or len(query.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query must be at least 3 characters long"
            )
        
        # Get or create session
        session = db_service.get_active_session_by_phone(phone_number)
        if not session:
            session_id = db_service.create_session(phone_number, {
                "phone_number": phone_number,
                "source": "api"
            })
            session = db_service.get_session(session_id)
        
        # Generate compliance response
        compliance_response = await watsonx_service.execute_compliance_workflow(
            query, session.context
        )
        
        # Save response in background
        background_tasks.add_task(
            db_service.save_compliance_response,
            session.session_id,
            phone_number,
            compliance_response
        )
        
        logger.info("Compliance query processed", 
                   user=current_user.get("sub"),
                   phone_number=phone_number,
                   total_cost=compliance_response.total_estimated_cost)
        
        return compliance_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error processing compliance query", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process compliance query"
        )


@router.post("/whatsapp/send")
async def send_whatsapp_message(
    message_request: WhatsAppMessageRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Send WhatsApp message.
    
    Args:
        message_request: Message request
        current_user: Authenticated user
        
    Returns:
        Dict: Send result
    """
    try:
        if message_request.message_type == "text":
            result = await whatsapp_service.send_text_message(
                message_request.to,
                message_request.message
            )
        elif message_request.message_type == "template":
            result = await whatsapp_service.send_template_message(
                message_request.to,
                message_request.template_name,
                message_request.template_params
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported message type"
            )
        
        logger.info("WhatsApp message sent via API", 
                   user=current_user.get("sub"),
                   to=message_request.to,
                   message_type=message_request.message_type)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error sending WhatsApp message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send WhatsApp message"
        )


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get session information.
    
    Args:
        session_id: Session ID
        current_user: Authenticated user
        
    Returns:
        Dict: Session information
    """
    try:
        session = db_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Get conversation history
        history = db_service.get_conversation_history(session_id, limit=20)
        
        return {
            "session": session.dict(),
            "conversation_history": history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting session", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session"
        )


@router.get("/sessions/phone/{phone_number}")
async def get_sessions_by_phone(
    phone_number: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get sessions by phone number.
    
    Args:
        phone_number: Phone number
        current_user: Authenticated user
        
    Returns:
        List[Dict]: List of sessions
    """
    try:
        # This would need to be implemented in database service
        # For now, return empty list
        return []
        
    except Exception as e:
        logger.error("Error getting sessions by phone", error=str(e), phone_number=phone_number)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )


@router.delete("/sessions/{session_id}")
async def deactivate_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Deactivate session.
    
    Args:
        session_id: Session ID
        current_user: Authenticated user
        
    Returns:
        Dict: Deactivation result
    """
    try:
        success = db_service.deactivate_session(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        logger.info("Session deactivated", 
                   user=current_user.get("sub"),
                   session_id=session_id)
        
        return {"status": "deactivated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deactivating session", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate session"
        )


@router.post("/admin/cleanup")
async def cleanup_old_sessions(
    days: int = 30,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Clean up old sessions.
    
    Args:
        days: Number of days to keep
        current_user: Authenticated user
        
    Returns:
        Dict: Cleanup result
    """
    try:
        # Check if user has admin privileges
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        cleaned_count = db_service.cleanup_old_sessions(days)
        
        logger.info("Old sessions cleaned up", 
                   user=current_user.get("sub"),
                   days=days,
                   cleaned_count=cleaned_count)
        
        return {
            "status": "success",
            "cleaned_sessions": cleaned_count,
            "days_retained": days
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cleaning up sessions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup sessions"
        )


@router.get("/config/validate")
async def validate_configuration(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Validate application configuration.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        Dict: Configuration validation result
    """
    try:
        # Check if user has admin privileges
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        is_valid = validate_environment()
        
        return {
            "valid": is_valid,
            "environment": settings.environment,
            "version": settings.app_version
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error validating configuration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate configuration"
        )
