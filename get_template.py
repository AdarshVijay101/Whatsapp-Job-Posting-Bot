import asyncio
import httpx
import json

async def fetch_templates():
    token = "EAAMriRuXs1UBQ9Q09jZBf2duXmsZCtWQLorBeHwLFYLL0ycSvx8BzrhrfSW3NkzGHMoAMuiaTIJ3Rahhkn72Vv3wRBJ8evE2Cs5YDFzik9qczUlLNMiHjIK3wKzl70CPkZAm3taHoYZCGsBRq5uzfIasovZASLYZC7A7lKjdrADiglCgfrP9w2CJffy2Gkv0zG5nLozpHm8lpIoeQqDVLSKKP1ELhZAg1ZAFllkmQ4QhyZCKrHxJzK8xm0b4uCA2jnYdD2E8ZCwjhBS3GMMkOBEI0YawZBD"
    
    url = "https://graph.facebook.com/v22.0/4315445828667569/message_templates?fields=name,language,status,components&name=job_post_notification"
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        with open("template.json", "w") as f:
            json.dump(resp.json(), f, indent=2)
        print("Template data saved to template.json")

if __name__ == "__main__":
    asyncio.run(fetch_templates())
