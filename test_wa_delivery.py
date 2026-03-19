import asyncio
import os
import json
import logging
from dotenv import load_dotenv
from app.integrations.whatsapp import WhatsAppClient
from app.validators.guardrails import ParsedJobData

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_delivery():
    load_dotenv()
    
    client = WhatsAppClient()
    
    # Mock data for testing
    parsed_data = ParsedJobData(
        job_title="E2E Webhook Test Engineer",
        location="Remote (Cloud)",
        salary="$150k - $200k",
        work_authorization="US Citizen / GC",
        job_summary="Testing the end-to-end WhatsApp status callback pipeline.",
        application_link="https://tillianai.com/jobs/test",
        employment_type="Full-time"
    )
    
    target_number = os.getenv("WA_ADMIN_NUMBER")
    if not target_number:
        print("ERROR: WA_ADMIN_NUMBER not found in .env")
        return

    print(f"\n--- Sending Test WhatsApp Message to {target_number} ---")
    msg_id, status, response = await client.send_template_message(
        target_number, 
        parsed_data, 
        "Tillian Test Bot",
        recruiter_email="test@tillianai.com"
    )
    
    print(f"\n[META API RESPONSE]")
    print(json.dumps(response, indent=2))
    print(f"\nInitial Status: {status}")
    print(f"Message ID: {msg_id}")
    
    if status == "SENT" or status == "ACCEPTED":
        print("\nSUCCESS: Message accepted by Meta.")
        print("NEXT STEP: Leave your backend running and check the terminal/database for 'DELIVERED' or 'READ' updates.")
        print("You should see: >>> [WA_STATUS UPDATE] in your uvicorn terminal.")
    else:
        print("\nFAILED: Message was not accepted by Meta.")

if __name__ == "__main__":
    asyncio.run(test_delivery())
