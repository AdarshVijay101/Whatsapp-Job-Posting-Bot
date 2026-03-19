import asyncio
import httpx
from app.config import settings

async def check_account():
    print("Checking Meta Account Status...")
    url = f"https://graph.facebook.com/{settings.whatsapp_api_version}/{settings.whatsapp_phone_number_id}"
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
    
    async with httpx.AsyncClient() as client:
        # Check Phone Number Status
        resp = await client.get(url, headers=headers)
        print(f"\nPhone Number Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))

        # Check Templates
        waba_id_url = f"https://graph.facebook.com/{settings.whatsapp_api_version}/{settings.whatsapp_phone_number_id}/?fields=whatsapp_business_account"
        resp = await client.get(waba_id_url, headers=headers)
        waba_id = resp.json().get("whatsapp_business_account", {}).get("id")
        
        if waba_id:
            print(f"\nFound WABA ID: {waba_id}")
            templates_url = f"https://graph.facebook.com/{settings.whatsapp_api_version}/{waba_id}/message_templates"
            resp = await client.get(templates_url, headers=headers)
            print(f"\nTemplates Status: {resp.status_code}")
            templates = resp.json().get("data", [])
            target = next((t for t in templates if t['name'] == settings.whatsapp_template_name), None)
            if target:
                print(f"Found Template '{settings.whatsapp_template_name}': Status={target.get('status')}")
            else:
                print(f"Template '{settings.whatsapp_template_name}' NOT FOUND in this account.")
        else:
            print("\nCould not find WABA ID from that Phone Number ID.")

if __name__ == "__main__":
    import json
    asyncio.run(check_account())
