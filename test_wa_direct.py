import asyncio
import json
from app.integrations.whatsapp import wa_client
from app.validators.guardrails import ParsedJobData
from app.config import settings

async def test_send():
    print(f"Testing WhatsApp Send...")
    print(f"Using Phone Number ID: {settings.whatsapp_phone_number_id}")
    print(f"Using Admin Number: {settings.wa_admin_number}")
    print(f"Using Template Name: {settings.whatsapp_template_name}")
    print(f"Token (First 10 chars): {settings.whatsapp_access_token[:10]}...")

    # Mock ParsedJobData
    mock_data = ParsedJobData(
        job_title="Test Software Engineer",
        location="Remote",
        salary="$100k",
        work_authorization="Citizen",
        job_summary="This is a test summary for WhatsApp delivery verification.",
        application_link="https://tillianai.com"
    )

    msg_id, status, response = await wa_client.send_template_message(
        settings.wa_admin_number, 
        mock_data, 
        "Test Submitter"
    )

    print(f"\nStatus: {status}")
    print(f"Message ID: {msg_id}")
    print(f"Raw Response: {response}")

if __name__ == "__main__":
    asyncio.run(test_send())
