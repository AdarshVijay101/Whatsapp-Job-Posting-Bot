import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def main():
    url = f"https://graph.facebook.com/{os.environ['WHATSAPP_API_VERSION']}/{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages"
    headers = {
        "Authorization": f"Bearer {os.environ['WHATSAPP_ACCESS_TOKEN']}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": os.environ['WA_ADMIN_NUMBER'],
        "type": "text",
        "text": {"body": "Test message from debug script!"}
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        print("Status", resp.status_code)
        print("Response", resp.json())

asyncio.run(main())
