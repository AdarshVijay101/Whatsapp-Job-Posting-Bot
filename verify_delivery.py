import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def verify_delivery():
    print("="*60)
    print("   WHATSAPP DELIVERY DIAGNOSTIC TOOL")
    print("="*60)
    
    token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    admin_number = os.getenv("WA_ADMIN_NUMBER")
    template_name = os.getenv("WHATSAPP_TEMPLATE_NAME")
    api_version = os.getenv("WHATSAPP_API_VERSION", "v22.0")
    
    print(f"[*] Phone Number ID: {phone_id}")
    print(f"[*] Sending To     : {admin_number}")
    print(f"[*] Template Name  : {template_name}")
    print("-" * 60)

    url = f"https://graph.facebook.com/{api_version}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": admin_number.replace("+", ""),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "parameter_name": "job_title", "text": "DIAGNOSTIC TEST ROLE"},
                        {"type": "text", "parameter_name": "location", "text": "Remote"},
                        {"type": "text", "parameter_name": "salary", "text": "$100/hr"},
                        {"type": "text", "parameter_name": "work_authorization", "text": "US Citizen"},
                        {"type": "text", "parameter_name": "submitter_name", "text": "Diagnostic Admin"},
                        {"type": "text", "parameter_name": "job_summary", "text": "This is a diagnostic message using named parameters."},
                        {"type": "text", "parameter_name": "application_link", "text": "https://developers.facebook.com"}
                    ]
                }
            ]
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            resp_json = response.json()
            
            print(f"\n[HTTP Status] {response.status_code}")
            print("[Raw Meta Response]")
            print(json.dumps(resp_json, indent=2))
            
            if response.status_code in [200, 201]:
                print("\n✅ SUCCESS: Meta accepted the request.")
                print("Wait 30-60 seconds to see if it arrives on your phone.")
                print("If it DOES NOT arrive, check your Meta Dashboard allowlist.")
            else:
                error = resp_json.get("error", {})
                code = error.get("code")
                subcode = error.get("error_subcode")
                message = error.get("message")
                
                print(f"\n❌ FAILURE: {message}")
                
                if code == 131030:
                    print("\n💡 TIP: Recipient not allowed. Your phone number is likely not added to the 'To' allowlist in the Meta API Setup page.")
                elif code == 132001:
                    print("\n💡 TIP: Template not found. Check if the template name OR language matches exactly.")
                elif code == 190:
                    print("\n💡 TIP: Token expired. You need to refresh your access token.")
                elif code == 100:
                    print("\n💡 TIP: Invalid parameter. Check your Phone Number ID or recipient formatting.")

        except Exception as e:
            print(f"\n🔥 CRITICAL ERROR: {e}")

    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(verify_delivery())
