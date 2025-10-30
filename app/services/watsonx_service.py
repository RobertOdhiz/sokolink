"""
Watsonx Orchestrate Direct Service
----------------------------------
- Uses IBM Cloud IAM (Bearer) authentication.
- Supports direct chat with Orchestrate agents using agent_id.
- Handles both simple and structured conversational requests.
- Includes retry logic, token caching, and structured logging.
"""

import json
import asyncio
import httpx
import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class WatsonxServiceDirect:
    """Direct integration with IBM Watsonx Orchestrate."""

    def __init__(self):
        self.base_url = (
            f"https://api.{settings.watsonx_region}.watson-orchestrate.cloud.ibm.com/"
            f"instances/{settings.watsonx_instance_id}"
        )
        self.api_key = settings.watsonx_api_key
        self.project_id = settings.watsonx_project_id
        self.instance_id = settings.watsonx_instance_id
        self.agent_id = settings.watsonx_agent_id  # from config/.env
        self._iam_token: Optional[str] = None
        self._iam_token_expiry: Optional[datetime] = None

        logger.info("Watsonx service initialized", base_url=self.base_url, agent_id=self.agent_id)

    # ---------------- MAIN PUBLIC FUNCTIONS ---------------- #

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=3, max=10),
           retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)))
    async def send_user_message(self, user_message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a simple user message to Watsonx Orchestrate."""
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
                "Watsonx Orchestrate returned an error",
                status=response.status_code,
                details=response.text,
            )
            raise Exception(f"Watsonx Orchestrate error: {response.text}")

    async def chat_with_agent(
        self,
        user_message: str,
        role: str = "user",
        additional_context: Optional[Dict[str, Any]] = None,
        stream: bool = True
    ) -> Dict[str, Any]:
        """
        Send a structured chat request directly to a specific agent via the Orchestrate API.
        """
        token = await self._get_iam_token()
        url = f"https://{settings.watsonx_api_endpoint}/api/v1/orchestrate/{self.agent_id}/chat/completions"

        # You can customize payload depending on your use case
        payload = {
            "messages": [
                {
                    "role": role,
                    "content": [
                        {
                            "response_type": "conversational_search",
                            "json_schema": {},
                            "ui_schema": {},
                            "form_data": {},
                            "id": "message_1",
                            "form_operation": "submit",
                            "sub_type": "text_input",
                            "event_type": "message",
                            "dps_payload_id": "payload_1"
                        },
                        {
                            "response_type": "text",
                            "text": user_message
                        }
                    ]
                }
            ],
            "additional_parameters": additional_context or {},
            "context": {},
            "stream": stream
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, headers=headers, json=payload)

        if resp.status_code != 200:
            logger.error("❌ chat_with_agent error", status=resp.status_code, text=resp.text)
            raise Exception(f"chat_with_agent failed: {resp.text}")

        data = resp.json()
        logger.info("💬 chat_with_agent successful", data=data)
        return data

    async def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Retrieve all messages from a Watsonx Orchestrate thread."""
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
                f"Watsonx Orchestrate message retrieval failed ({resp.status_code}): {resp.text}"
            )

        return resp.json()

    async def wait_for_assistant_reply(self, thread_id: str, max_attempts: int = 10, delay: int = 3) -> Optional[str]:
        """Poll Orchestrate for an assistant's response."""
        thinking_messages = [
            "💭 Thinking...",
            "🤔 Let me check that for you...",
            "🧠 Processing your request...",
            "🔍 Gathering insights...",
            "⌛ Almost there..."
        ]

        for attempt in range(max_attempts):
            logger.info(thinking_messages[attempt % len(thinking_messages)])
            messages = await self.get_thread_messages(thread_id)

            for msg in messages:
                if msg.get("role") == "assistant":
                    for block in msg.get("content", []):
                        if block.get("response_type") == "text":
                            return block.get("text")

            await asyncio.sleep(delay)

        return None

    async def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Full chat sequence:
        - Send a message
        - Poll Orchestrate for the assistant's response
        - Return user-facing message
        """
        run_data = await self.send_user_message(user_message)
        thread_id = run_data.get("thread_id")

        if not thread_id:
            raise ValueError("No thread_id returned from Orchestrate.")

        assistant_reply = await self.wait_for_assistant_reply(thread_id)

        if assistant_reply:
            return {
                "success": True,
                "thread_id": thread_id,
                "reply": assistant_reply
            }
        else:
            return {
                "success": False,
                "thread_id": thread_id,
                "reply": "⚠️ No response received yet. Please try again in a moment."
            }

    # ---------------- INTERNAL HELPERS ---------------- #

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
