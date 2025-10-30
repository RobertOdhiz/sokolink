"""
Watsonx Orchestrate Direct Service
----------------------------------
- Uses IBM Cloud IAM (Bearer) authentication.
- Sends user messages directly to Watson Orchestrate chat endpoint.
- Returns only the real message content from Orchestrate.
"""

import json
import httpx
import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class WatsonxServiceDirect:
    """Direct integration with IBM Watson Orchestrate."""

    def __init__(self):
        self.base_url = (
            f"https://api.{settings.watsonx_region}.watson-orchestrate.cloud.ibm.com/"
            f"instances/{settings.watsonx_instance_id}"
        )
        self.api_key = settings.watsonx_api_key
        self.project_id = settings.watsonx_project_id
        self.instance_id = settings.watsonx_instance_id
        self._iam_token: Optional[str] = None
        self._iam_token_expiry: Optional[datetime] = None

        logger.info("Watsonx service initialized", base_url=self.base_url)

    # ---------------- MAIN PUBLIC FUNCTION ---------------- #

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=3, max=10),
           retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)))
    async def send_user_message(self, user_message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a user message directly to WatsonX Orchestrate (creates a run/thread)."""
        orchestrate_url = f"{self.base_url}/v1/orchestrate/runs?stream=false&multiple_content=false"

        payload = {
            "message": {
                "role": "user",
                "content": [
                    {
                        "response_type": "text",
                        "text": user_message
                    }
                ]
            }
        }

        headers = await self._get_auth_headers()

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(orchestrate_url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Message sent successfully", data=data)
            return data
        else:
            logger.error(
                "Watson Orchestrate returned an error",
                status=response.status_code,
                details=response.text,
            )
            raise Exception(f"Watsonx Orchestrate error: {response.text}")


    async def get_thread_messages(self, thread_id: str) -> Dict[str, Any]:
        """
        Retrieve all messages from a Watson Orchestrate thread.
        """
        token = await self._get_iam_token()
        url = f"{self.base_url}/v1/orchestrate/threads/{thread_id}/messages"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code != 200:
            raise RuntimeError(
                f"Watson Orchestrate message retrieval failed ({resp.status_code}): {resp.text}"
            )

        return resp.json()



    # ---------------- INTERNAL HELPERS ---------------- #

    def _extract_user_message(self, data: Dict[str, Any]) -> str:
        """
        Extracts the message text returned by Orchestrate.
        """
        try:
            # Depending on Orchestrate run output structure
            messages = data.get("messages") or data.get("choices") or []
            if not messages:
                return "No response message found."

            # If messages are structured as in Orchestrate Run API
            for msg in messages:
                if msg.get("role") == "assistant" and "content" in msg:
                    content = msg["content"]
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        return " ".join(
                            [blk.get("text", "") for blk in content if blk.get("text")]
                        ).strip()

            # Fallback if assistant not found explicitly
            return json.dumps(messages, indent=2)

        except Exception as e:
            logger.error("Failed to parse Orchestrate response", error=str(e))
            return "Could not extract message from Orchestrate response."

    async def _get_auth_headers(self) -> Dict[str, str]:
        """Retrieve or refresh IAM token."""
        token = await self._get_iam_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _get_iam_token(self) -> str:
        """Get IBM Cloud IAM token (cached until expiry)."""
        if (
            self._iam_token
            and self._iam_token_expiry
            and datetime.utcnow() < (self._iam_token_expiry - timedelta(minutes=5))
        ):
            return self._iam_token

        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": self.api_key,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post("https://iam.cloud.ibm.com/identity/token", data=data, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
            self._iam_token = payload["access_token"]
            self._iam_token_expiry = datetime.utcnow() + timedelta(seconds=int(payload.get("expires_in", 3600)))
            return self._iam_token


# Singleton instance
watsonx_service = WatsonxServiceDirect()
