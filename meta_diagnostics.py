import asyncio
import httpx
import json
from app.config import settings

async def list_everything():
    print("=== Meta API Diagnostics ===")
    token = settings.whatsapp_access_token
    version = settings.whatsapp_api_version
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        # 1. Get User Info / Apps
        print("\n1. GET /me (Token Owner Info)")
        resp = await client.get(f"https://graph.facebook.com/{version}/me", headers=headers)
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))

        # 2. List WABAs the token can see
        print("\n2. GET /me/whatsapp_business_accounts")
        resp = await client.get(f"https://graph.facebook.com/{version}/me/whatsapp_business_accounts", headers=headers)
        print(f"Status: {resp.status_code}")
        wabas = resp.json().get('data', [])
        print(json.dumps(wabas, indent=2))

        for waba in wabas:
            waba_id = waba['id']
            print(f"\n--- Checking WABA: {waba_id} ---")
            
            # List phone numbers for this WABA
            print(f"GET /{waba_id}/phone_numbers")
            resp = await client.get(f"https://graph.facebook.com/{version}/{waba_id}/phone_numbers", headers=headers)
            phones = resp.json().get('data', [])
            print(json.dumps(phones, indent=2))

            # List templates for this WABA
            print(f"GET /{waba_id}/message_templates")
            resp = await client.get(f"https://graph.facebook.com/{version}/{waba_id}/message_templates", headers=headers)
            templates = resp.json().get('data', [])
            print(f"Found {len(templates)} templates.")
            for t in templates:
                if t['name'] == settings.whatsapp_template_name:
                    print(f"MATCH FOUND: {t['name']} (Status: {t['status']}, Lang: {t['language']})")

if __name__ == "__main__":
    asyncio.run(list_everything())
