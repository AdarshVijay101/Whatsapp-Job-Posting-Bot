import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def get_live_template():
    token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    version = os.getenv("WHATSAPP_API_VERSION", "v22.0")
    # WABA ID from get_template.py
    waba_id = "4315445828667569" 
    
    url = f"https://graph.facebook.com/{version}/{waba_id}/message_templates?name=job_post_notification"
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(json.dumps(data, indent=2))
        
        if resp.status_code == 200:
            with open("live_template.json", "w") as f:
                json.dump(data, f, indent=2)

if __name__ == "__main__":
    asyncio.run(get_live_template())
