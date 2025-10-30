import asyncio
import os
from typing import Any, Dict

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def mask_token(token: str, show: int = 6) -> str:
    if not token or len(token) <= show * 2:
        return "***"
    return f"{token[:show]}...{token[-show:]}"


async def run_tests() -> None:
    if load_dotenv:
        load_dotenv()

    from app.services.watsonx_service import watsonx_service
    from app.config import get_settings

    settings = get_settings()

    print("\n=== Watsonx Orchestrate Direct Service Test ===")
    print("Base URL:", settings.watsonx_base_url)
    print("Instance ID:", settings.watsonx_instance_id)
    print("Project ID:", settings.watsonx_project_id)

    # 1️⃣ IAM Token
    print("\n[1] Fetching IAM token...")
    try:
        token = await watsonx_service._get_iam_token()
        print("✅ IAM Token:", mask_token(token))
    except Exception as e:
        print("❌ IAM token retrieval failed:", e)
        return

    # 2️⃣ Send Message
    print("\n[2] Sending message to Watson Orchestrate...")
    try:
        response: Dict[str, Any] = await watsonx_service.send_user_message("I am Amina, I own a small business in Kibera that sells sweets in Nairobi?")
        print("\n✅ Orchestrate Response:")
        print(response)
    except Exception as e:
        print("❌ Message test failed:", e)
        return

    thread_id = response.get("thread_id")
    if not thread_id:
        print("⚠️ No thread_id returned, cannot fetch messages.")
        return

    # 3️⃣ Fetch Messages
    print("\n[3] Fetching messages from Orchestrate thread...")
    try:
        messages: Dict[str, Any] = await watsonx_service.get_thread_messages(thread_id)
        print("\n✅ Thread Messages:")
        print(messages)
    except Exception as e:
        print("❌ Failed to fetch messages:", e)
        return

    print("\n🎯 All tests completed successfully!\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
