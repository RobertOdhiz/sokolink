import asyncio
import os
import sys
import itertools
from typing import Any, Dict

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def mask_token(token: str, show: int = 6) -> str:
    if not token or len(token) <= show * 2:
        return "***"
    return f"{token[:show]}...{token[-show:]}"


async def spinner(message: str, event: asyncio.Event):
    """Simple async spinner animation."""
    for frame in itertools.cycle(["⏳", "🤔", "💭", "🔄"]):
        if event.is_set():
            break
        sys.stdout.write(f"\r{frame} {message}")
        sys.stdout.flush()
        await asyncio.sleep(0.3)
    sys.stdout.write("\r✅ Done!\n")


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
    token_event = asyncio.Event()
    spinner_task = asyncio.create_task(spinner("Getting access token from IBM Cloud...", token_event))
    try:
        token = await watsonx_service._get_iam_token()
        token_event.set()
        await spinner_task
        print("✅ IAM Token:", mask_token(token))
    except Exception as e:
        token_event.set()
        print(f"\n❌ IAM token retrieval failed: {e}")
        return

    # 2️⃣ Chat With Agent
    print("\n[2] Initiating chat with Watsonx Orchestrate Agent...")
    chat_event = asyncio.Event()
    spinner_task = asyncio.create_task(spinner("Chatting with Watsonx agent...", chat_event))
    try:
        # Example message
        user_message = "I am Amina, I own a small business in Kibera that sells sweets in Nairobi."
        response: Dict[str, Any] = await watsonx_service.chat_with_agent(user_message)

        chat_event.set()
        await spinner_task

        print("\n✅ Agent Chat Response:")
        print(response)

        # Optional: extract structured output
        if isinstance(response, dict):
            print("\n🧠 Agent message summary:")
            if "reply" in response:
                print(response["reply"])
            elif "messages" in response:
                for msg in response["messages"]:
                    print(f"- {msg.get('content', '')}")
    except Exception as e:
        chat_event.set()
        print(f"\n❌ Chat with agent failed: {e}")
        return

    print("\n🎯 All tests completed successfully!\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
