"""
WhatsApp Business API service for sending and receiving messages.
Updated to support sending responses from Orchestrate-style agents (IBM watsonx),
including simple text replies and simple interactive button conversions when the
orchestrate response contains an "options" or "buttons" list.
"""

import json
from typing import Dict, Any, Optional, List, Sequence
from datetime import datetime
import httpx
import structlog
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings
from app.models.response_models import WhatsAppMessageRequest
from app.utils.formatters import (
    format_whatsapp_message,
    format_whatsapp_message_short,
    split_long_message,
)

logger = structlog.get_logger()
settings = get_settings()


class WhatsAppService:
    """Service for interacting with WhatsApp Business API."""

    def __init__(self):
        """Initialize WhatsApp service."""
        self.access_token: str = settings.whatsapp_access_token
        self.phone_number_id: str = settings.whatsapp_phone_number_id
        # Expect api version like "v17.0" or "v18.0"
        self.api_version: str = settings.whatsapp_api_version

        # Base URL for sending messages:
        # Note: `messages` endpoint will be appended when making requests.
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        logger.info(
            "WhatsApp service initialized",
            phone_number_id=self.phone_number_id,
            api_version=self.api_version,
        )

    # ---------------- Public sending helpers ---------------- #

    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send text message via WhatsApp.

        Args:
            to: Recipient phone number (E.164 format without +, or as WhatsApp expects)
            message: Message content

        Returns:
            Dict: API response (first chunk's response wrapped in dict)
        """
        try:
            message_chunks = split_long_message(message)
            responses: List[Dict[str, Any]] = []
            for chunk in message_chunks:
                response = await self._send_single_message(to, chunk)
                responses.append(response)
                if len(message_chunks) > 1:
                    await asyncio.sleep(0.5)

            logger.info(
                "Text message sent",
                to=to,
                chunks=len(message_chunks),
                total_length=len(message),
            )

            # Return the first response (typical behaviour) with some metadata
            first_resp = responses[0] if responses else {}
            return {
                "success": True,
                "message_id": first_resp.get("messages", [{}])[0].get("id")
                if first_resp.get("messages")
                else None,
                "chunks_sent": len(message_chunks),
                "raw_responses": responses,
            }

        except Exception as e:
            logger.error("Error sending text message", error=str(e), to=to)
            raise

    async def send_template_message(
        self, to: str, template_name: str, template_params: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send template message via WhatsApp.
        """
        try:
            payload: Dict[str, Any] = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {"name": template_name, "language": {"code": "en"}},
            }

            if template_params:
                payload["template"]["components"] = [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": param} for param in template_params],
                    }
                ]

            response = await self._make_api_call("messages", payload)
            logger.info("Template message sent", to=to, template=template_name, params=template_params)
            return response

        except Exception as e:
            logger.error("Error sending template message", error=str(e), to=to)
            raise

    async def send_interactive_message(
        self, to: str, header_text: str, body_text: str, footer_text: str, buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Send interactive message with reply buttons (max 3).
        `buttons` is a list of dicts each containing "id" and "title".
        """
        try:
            # WhatsApp supports up to 3 reply buttons
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
                                "reply": {"id": button["id"], "title": button["title"]},
                            }
                            for button in buttons
                        ]
                    },
                },
            }

            response = await self._make_api_call("messages", payload)
            logger.info("Interactive message sent", to=to, buttons=len(buttons))
            return response

        except Exception as e:
            logger.error("Error sending interactive message", error=str(e), to=to)
            raise

    async def send_compliance_response(self, to: str, compliance_response: Any, format_type: str = "full") -> Dict[str, Any]:
        """
        Send a compliance response to the user.
        `compliance_response` is an arbitrary structure expected by your formatters.
        """
        try:
            if format_type == "short":
                message = format_whatsapp_message_short(compliance_response)
            else:
                message = format_whatsapp_message(compliance_response)

            # Send the main text
            response = await self.send_text_message(to, message)

            # Offer follow-up interactive options
            buttons = [
                {"id": "details", "title": "📋 Full Details"},
                {"id": "summary", "title": "📊 Summary"},
                {"id": "help", "title": "🆘 Help"},
            ]

            await self.send_interactive_message(
                to=to,
                header_text="Need more information?",
                body_text="Choose an option below:",
                footer_text="Sokolink Advisor",
                buttons=buttons,
            )

            logger.info(
                "Compliance response sent",
                to=to,
                format_type=format_type,
                # `compliance_response` is arbitrary; guard access to attributes
                total_cost=getattr(compliance_response, "total_estimated_cost", None),
            )

            return response

        except Exception as e:
            logger.error("Error sending compliance response", error=str(e), to=to)
            raise

    async def send_welcome_message(self, to: str) -> Dict[str, Any]:
        """Send welcome message to new user."""
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
        """Send help message to user."""
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
        """Send an error message to the user."""
        from app.utils.formatters import format_error_message

        try:
            message = format_error_message(error_code, error_message)
            response = await self.send_text_message(to, message)
            logger.info("Error message sent", to=to, error_code=error_code)
            return response

        except Exception as e:
            logger.error("Error sending error message", error=str(e), to=to)
            raise

    # ---------------- Orchestrate integration helpers ---------------- #

    async def send_orchestrate_response(self, to: str, orchestrate_response: Any) -> Dict[str, Any]:
        """
        Send back a response produced by an orchestrate agent (e.g. WatsonxServiceDirect.chat result).
        This function attempts to intelligently extract text and optional interactive options.
        Supported orchestrate_response shapes:
          - {"reply": "text..."}                      -> sends text
          - {"message": "text..."}                    -> sends text
          - {"options": ["A","B"]}                    -> sends text + buttons derived from options
          - {"buttons": [{"id":"x","title":"X"}]}     -> sends interactive buttons
          - complex nested dicts: attempts to pull the first found textual content
        """
        try:
            # If the response is a string, just send it
            if isinstance(orchestrate_response, str):
                return await self.send_text_message(to, orchestrate_response)

            # Safely try to extract explicit fields first
            if isinstance(orchestrate_response, dict):
                # Common wrapper that some wrappers return
                if "reply" in orchestrate_response and isinstance(orchestrate_response["reply"], str):
                    return await self.send_text_message(to, orchestrate_response["reply"])

                if "message" in orchestrate_response and isinstance(orchestrate_response["message"], str):
                    return await self.send_text_message(to, orchestrate_response["message"])

                # If agent wrapper used earlier: {"success": True, "reply": "..."}
                if orchestrate_response.get("success") and isinstance(orchestrate_response.get("reply"), str):
                    return await self.send_text_message(to, orchestrate_response["reply"])

                # If explicit buttons provided
                if "buttons" in orchestrate_response and isinstance(orchestrate_response["buttons"], Sequence):
                    buttons_raw = orchestrate_response["buttons"]
                    buttons: List[Dict[str, str]] = []
                    for b in buttons_raw[:3]:
                        # Accept either simple strings or dicts with id/title
                        if isinstance(b, str):
                            buttons.append({"id": f"opt_{len(buttons)+1}", "title": b[:20]})
                        elif isinstance(b, dict):
                            bid = str(b.get("id") or b.get("value") or f"opt_{len(buttons)+1}")
                            title = str(b.get("title") or b.get("label") or bid)[:20]
                            buttons.append({"id": bid, "title": title})
                    # Body text fallback
                    body_text = self._extract_text_from_orchestrate(orchestrate_response) or "Choose an option:"
                    return await self.send_interactive_message(
                        to=to, header_text=body_text[:60], body_text=body_text, footer_text="Sokolink Advisor", buttons=buttons
                    )

                # If options array of simple strings -> convert to buttons
                if "options" in orchestrate_response and isinstance(orchestrate_response["options"], Sequence):
                    opts = orchestrate_response["options"]
                    buttons = [{"id": f"opt_{i+1}", "title": str(opt)[:20]} for i, opt in enumerate(opts[:3])]
                    body_text = self._extract_text_from_orchestrate(orchestrate_response) or "Choose an option:"
                    return await self.send_interactive_message(
                        to=to, header_text=body_text[:60], body_text=body_text, footer_text="Sokolink Advisor", buttons=buttons
                    )

            # Fallback: try to extract a text blob from nested dicts/lists
            extracted = self._extract_text_from_orchestrate(orchestrate_response)
            if extracted:
                return await self.send_text_message(to, extracted)

            # Last resort: send a JSON preview (limited size)
            preview = json.dumps(orchestrate_response, default=str)
            if len(preview) > 1500:
                preview = preview[:1496] + "..."
            preview_msg = f"Response:\n{preview}"
            return await self.send_text_message(to, preview_msg)

        except Exception as e:
            logger.error("Error sending orchestrate response", error=str(e), to=to)
            raise

    def _extract_text_from_orchestrate(self, payload: Any) -> Optional[str]:
        """
        Attempt to walk a nested orchestrate response and collect the first/most relevant text
        fields. This is conservative and only pulls values from obvious keys to avoid
        inventing behavior.
        """
        # Helper inner function: look for keys commonly used for text
        text_keys = {"text", "reply", "message", "output", "summary", "content"}
        found_texts: List[str] = []

        def walk(obj: Any):
            if obj is None:
                return
            if isinstance(obj, str):
                found_texts.append(obj)
                return
            if isinstance(obj, dict):
                for k, v in obj.items():
                    # prioritize known text keys
                    if k in text_keys and isinstance(v, str):
                        found_texts.append(v)
                        # don't return immediately; gather a few
                    else:
                        walk(v)
            elif isinstance(obj, (list, tuple)):
                for item in obj:
                    walk(item)

        try:
            walk(payload)
        except Exception:
            # Defensive: if anything goes wrong, don't raise from extractor
            return None

        if not found_texts:
            return None

        # Join multiple found texts into a coherent short message
        joined = "\n\n".join(found_texts[:8])
        # Limit length to WhatsApp-friendly size (approx)
        if len(joined) > 4096:
            return joined[:4092] + "..."
        return joined

    # ---------------- Core HTTP helpers ---------------- #

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def _send_single_message(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send a single text chunk via WhatsApp API (wrapped by retry logic).
        """
        payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}}
        return await self._make_api_call("messages", payload)

    async def _make_api_call(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make API call to WhatsApp Business API.
        The `endpoint` is appended to the base URL. Example: endpoint="messages"
        """
        url = f"{self.base_url}/{endpoint}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                result = response.json()
                logger.debug("WhatsApp API call successful", endpoint=endpoint, status_code=response.status_code)
                return result
            except httpx.HTTPStatusError as e:
                # Log error body for debugging
                try:
                    resp_text = e.response.text
                except Exception:
                    resp_text = "<no-response-body>"
                logger.error(
                    "WhatsApp API error",
                    endpoint=endpoint,
                    status_code=e.response.status_code if e.response is not None else "unknown",
                    response_text=resp_text,
                )
                raise
            except httpx.TimeoutException:
                logger.error("WhatsApp API timeout", endpoint=endpoint)
                raise
            except Exception as e:
                logger.error("Unexpected error calling WhatsApp API", endpoint=endpoint, error=str(e))
                raise

    async def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get message delivery status.
        """
        try:
            url = f"{self.base_url}/messages/{message_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error("Error getting message status", message_id=message_id, error=str(e))
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Check WhatsApp service health by fetching phone number details.
        """
        try:
            url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self.headers)
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "response_time": response.elapsed.total_seconds(),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                else:
                    return {"status": "unhealthy", "status_code": response.status_code, "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            logger.error("WhatsApp health check failed", error=str(e))
            return {"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()}


# Global WhatsApp service instance
whatsapp_service = WhatsAppService()
