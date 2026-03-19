import asyncio
import httpx
import json
from app.config import settings

async def robust_check():
    token = settings.whatsapp_access_token
    phone_id = settings.whatsapp_phone_number_id
    version = settings.whatsapp_api_version
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        # 1. Get Phone ID Details and WABA ID
        print(f"--- Checking Phone ID: {phone_id} ---")
        url = f"https://graph.facebook.com/{version}/{phone_id}?fields=whatsapp_business_account,verified_name,display_phone_number"
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Error fetching phone info: {resp.text}")
            return
        
        data = resp.json()
        print(json.dumps(data, indent=2))
        
        waba_id = data.get('whatsapp_business_account', {}).get('id')
        if not waba_id:
            print("WABA ID not found in phone response.")
            return

        print(f"\n--- WABA ID: {waba_id} ---")

        # 2. List Templates and find exact match
        print(f"Checking for template: {settings.whatsapp_template_name}")
        url = f"https://graph.facebook.com/{version}/{waba_id}/message_templates"
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Error fetching templates: {resp.text}")
            return

        templates = resp.json().get('data', [])
        found = False
        for t in templates:
            if t['name'] == settings.whatsapp_template_name:
                found = True
                print(f"\n[MATCH FOUND]")
                print(f"Name: {t['name']}")
                print(f"Status: {t['status']}")
                print(f"Category: {t['category']}")
                print(f"Language: {t['language']}")
                print("Components:")
                print(json.dumps(t.get('components', []), indent=2))
        
        if not found:
            print(f"\n[NOT FOUND] Template '{settings.whatsapp_template_name}' not in this account.")
            print("Available templates in first batch:")
            for t in templates[:10]:
                print(f"- {t['name']} ({t['status']}, {t['language']})")

if __name__ == "__main__":
    asyncio.run(robust_check())
