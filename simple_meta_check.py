import asyncio
import httpx
import json
from app.config import settings

async def simple_check():
    token = settings.whatsapp_access_token
    phone_id = settings.whatsapp_phone_number_id
    version = settings.whatsapp_api_version # v22.0
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        # Check Token Info via debug_token
        # We need an App Access Token for this, but we can try to get app info first
        print("Checking Application Info...")
        resp = await client.get(f"https://graph.facebook.com/{version}/app", headers=headers)
        print(f"App Info: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))

        # Check Phone Number directly
        print(f"\nChecking Phone Number ID: {phone_id}")
        resp = await client.get(f"https://graph.facebook.com/{version}/{phone_id}", headers=headers)
        print(f"Phone Status: {resp.status_code}")
        phone_data = resp.json()
        print(json.dumps(phone_data, indent=2))

        # Get WABA ID
        waba_id = phone_data.get('whatsapp_business_account', {}).get('id')
        if waba_id:
            print(f"\nFound WABA ID: {waba_id}")
            # Check Templates
            print(f"Checking templates for WABA: {waba_id}")
            resp = await client.get(f"https://graph.facebook.com/{version}/{waba_id}/message_templates", headers=headers)
            print(f"Templates Status: {resp.status_code}")
            templates = resp.json().get('data', [])
            print(f"Total Templates: {len(templates)}")
            for t in templates:
                if t['name'] == settings.whatsapp_template_name:
                    print(f"-> MATCH FOUND: {t['name']} (Status: {t['status']}, Lang: {t['language']})")
        else:
            print("\nCould not resolve WABA ID from Phone ID.")

if __name__ == "__main__":
    asyncio.run(simple_check())
