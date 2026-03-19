import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def debug_send():
    print("=== WhatsApp Independent Debug Utility ===")
    
    token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    to_number = os.getenv("WA_ADMIN_NUMBER")
    template_name = os.getenv("WHATSAPP_TEMPLATE_NAME")
    api_version = os.getenv("WHATSAPP_API_VERSION", "v22.0")
    
    if not all([token, phone_id, to_number, template_name]):
        print("ERROR: Missing one or more required environment variables (TOKEN, PHONE_ID, ADMIN_NUMBER, TEMPLATE_NAME)")
        return

    url = f"https://graph.facebook.com/{api_version}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Standard dummy data matching your template parameters
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number.replace("+", ""),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": "DEBUG JOB TITLE"},
                        {"type": "text", "text": "DEBUG LOCATION"},
                        {"type": "text", "text": "DEBUG SALARY"},
                        {"type": "text", "text": "DEBUG WORK AUTH"},
                        {"type": "text", "text": "DEBUG SUBMITTER"},
                        {"type": "text", "text": "DEBUG SUMMARY"},
                        {"type": "text", "text": "https://example.com/debug"}
                    ]
                }
            ]
        }
    }

    async with httpx.AsyncClient() as client:
        print(f"Sending request to: {url}")
        print(f"To: {to_number}")
        print(f"Template: {template_name}")
        
        try:
            response = await client.post(url, json=payload, headers=headers)
            print(f"\nStatus Code: {response.status_code}")
            print("Response Payload:")
            print(json.dumps(response.json(), indent=2))
            
            if response.status_code in [200, 201]:
                print("\nSUCCESS: Message accepted by Meta.")
            else:
                print("\nFAILURE: Check error details above.")
        except Exception as e:
            print(f"\nERROR: Network request failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_send())
