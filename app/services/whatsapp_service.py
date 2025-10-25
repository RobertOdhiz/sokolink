"""
WhatsApp Business API service for sending and receiving messages.
"""
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings
from app.models.response_models import WhatsAppMessageRequest
from app.utils.formatters import format_whatsapp_message, format_whatsapp_message_short, split_long_message

logger = structlog.get_logger()
settings = get_settings()


class WhatsAppService:
    """Service for interacting with WhatsApp Business API."""
    
    def __init__(self):
        """Initialize WhatsApp service."""
        self.access_token = settings.whatsapp_access_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.api_version = settings.whatsapp_api_version
        
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
        
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        logger.info("WhatsApp service initialized", 
                   phone_number_id=self.phone_number_id,
                   api_version=self.api_version)
    
    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send text message via WhatsApp.
        
        Args:
            to: Recipient phone number
            message: Message content
            
        Returns:
            Dict: API response
        """
        try:
            # Split long messages
            message_chunks = split_long_message(message)
            
            responses = []
            for chunk in message_chunks:
                response = await self._send_single_message(to, chunk)
                responses.append(response)
                
                # Small delay between chunks
                if len(message_chunks) > 1:
                    await asyncio.sleep(0.5)
            
            logger.info("Text message sent", 
                       to=to, 
                       chunks=len(message_chunks),
                       total_length=len(message))
            
            return {
                "success": True,
                "message_id": responses[0].get("messages", [{}])[0].get("id") if responses else None,
                "chunks_sent": len(message_chunks)
            }
            
        except Exception as e:
            logger.error("Error sending text message", error=str(e), to=to)
            raise
    
    async def send_template_message(self, to: str, template_name: str, 
                                  template_params: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send template message via WhatsApp.
        
        Args:
            to: Recipient phone number
            template_name: Template name
            template_params: Template parameters
            
        Returns:
            Dict: API response
        """
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en"}
                }
            }
            
            # Add parameters if provided
            if template_params:
                payload["template"]["components"] = [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": param} for param in template_params]
                }]
            
            response = await self._make_api_call("messages", payload)
            
            logger.info("Template message sent", 
                       to=to, 
                       template=template_name,
                       params=template_params)
            
            return response
            
        except Exception as e:
            logger.error("Error sending template message", error=str(e), to=to)
            raise
    
    async def send_interactive_message(self, to: str, header_text: str, body_text: str, 
                                     footer_text: str, buttons: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Send interactive message with buttons.
        
        Args:
            to: Recipient phone number
            header_text: Header text
            body_text: Body text
            footer_text: Footer text
            buttons: List of button configurations
            
        Returns:
            Dict: API response
        """
        try:
            # Limit to 3 buttons for WhatsApp
            buttons = buttons[:3]
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "header": {"type": "text", "text": header_text},
                    "body": {"text": body_text},
                    "footer": {"text": footer_text},
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": button["id"],
                                    "title": button["title"]
                                }
                            }
                            for button in buttons
                        ]
                    }
                }
            }
            
            response = await self._make_api_call("messages", payload)
            
            logger.info("Interactive message sent", 
                       to=to, 
                       buttons=len(buttons))
            
            return response
            
        except Exception as e:
            logger.error("Error sending interactive message", error=str(e), to=to)
            raise
    
    async def send_compliance_response(self, to: str, compliance_response: Any, 
                                     format_type: str = "full") -> Dict[str, Any]:
        """
        Send compliance response formatted for WhatsApp.
        
        Args:
            to: Recipient phone number
            compliance_response: Compliance response data
            format_type: "full" or "short"
            
        Returns:
            Dict: API response
        """
        try:
            if format_type == "short":
                message = format_whatsapp_message_short(compliance_response)
            else:
                message = format_whatsapp_message(compliance_response)
            
            # Send the main message
            response = await self.send_text_message(to, message)
            
            # Send interactive buttons for follow-up
            buttons = [
                {"id": "details", "title": "📋 Full Details"},
                {"id": "summary", "title": "📊 Summary"},
                {"id": "help", "title": "🆘 Help"}
            ]
            
            await self.send_interactive_message(
                to=to,
                header_text="Need more information?",
                body_text="Choose an option below:",
                footer_text="Sokolink Advisor",
                buttons=buttons
            )
            
            logger.info("Compliance response sent", 
                       to=to, 
                       format_type=format_type,
                       total_cost=compliance_response.total_estimated_cost)
            
            return response
            
        except Exception as e:
            logger.error("Error sending compliance response", error=str(e), to=to)
            raise
    
    async def send_welcome_message(self, to: str) -> Dict[str, Any]:
        """
        Send welcome message to new user.
        
        Args:
            to: Recipient phone number
            
        Returns:
            Dict: API response
        """
        from app.utils.formatters import format_welcome_message
        
        try:
            message = format_welcome_message()
            response = await self.send_text_message(to, message)
            
            logger.info("Welcome message sent", to=to)
            return response
            
        except Exception as e:
            logger.error("Error sending welcome message", error=str(e), to=to)
            raise
    
    async def send_help_message(self, to: str) -> Dict[str, Any]:
        """
        Send help message to user.
        
        Args:
            to: Recipient phone number
            
        Returns:
            Dict: API response
        """
        from app.utils.formatters import format_help_message
        
        try:
            message = format_help_message()
            response = await self.send_text_message(to, message)
            
            logger.info("Help message sent", to=to)
            return response
            
        except Exception as e:
            logger.error("Error sending help message", error=str(e), to=to)
            raise
    
    async def send_error_message(self, to: str, error_code: str, error_message: str) -> Dict[str, Any]:
        """
        Send error message to user.
        
        Args:
            to: Recipient phone number
            error_code: Error code
            error_message: Error message
            
        Returns:
            Dict: API response
        """
        from app.utils.formatters import format_error_message
        
        try:
            message = format_error_message(error_code, error_message)
            response = await self.send_text_message(to, message)
            
            logger.info("Error message sent", to=to, error_code=error_code)
            return response
            
        except Exception as e:
            logger.error("Error sending error message", error=str(e), to=to)
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _send_single_message(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send single message via WhatsApp API.
        
        Args:
            to: Recipient phone number
            message: Message content
            
        Returns:
            Dict: API response
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        
        return await self._make_api_call("messages", payload)
    
    async def _make_api_call(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make API call to WhatsApp Business API.
        
        Args:
            endpoint: API endpoint
            payload: Request payload
            
        Returns:
            Dict: API response
        """
        url = f"{self.base_url}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                logger.debug("WhatsApp API call successful", 
                           endpoint=endpoint,
                           status_code=response.status_code)
                
                return result
                
            except httpx.HTTPStatusError as e:
                logger.error("WhatsApp API error", 
                           endpoint=endpoint,
                           status_code=e.response.status_code,
                           response_text=e.response.text)
                raise
            except httpx.TimeoutException:
                logger.error("WhatsApp API timeout", endpoint=endpoint)
                raise
            except Exception as e:
                logger.error("Unexpected error calling WhatsApp API", 
                           endpoint=endpoint,
                           error=str(e))
                raise
    
    async def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get message delivery status.
        
        Args:
            message_id: Message ID
            
        Returns:
            Dict: Message status
        """
        try:
            url = f"{self.base_url}/messages/{message_id}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            logger.error("Error getting message status", 
                        message_id=message_id,
                        error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check WhatsApp service health.
        
        Returns:
            Dict: Health check result
        """
        try:
            # Try to get phone number info
            url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "response_time": response.elapsed.total_seconds(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "status_code": response.status_code,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error("WhatsApp health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global WhatsApp service instance
whatsapp_service = WhatsAppService()
