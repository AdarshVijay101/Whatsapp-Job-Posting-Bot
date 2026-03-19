import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def main():
    from app.validators.guardrails import JobSubmission
    from app.main import parse_tally_payload
    from app.integrations.whatsapp import wa_client

    try:
        with open("last_req.json", "r", encoding="utf-8", errors="replace") as f:
            payload = json.load(f)
            
            for field in payload.get("data", {}).get("fields", []):
                if str(field.get("label", "")).strip().lower() in ["application link", "apply link"]:
                    val = str(field.get("value", ""))
                    if val and not val.startswith("http"):
                        field["value"] = f"https://{val}"

        parsed_data, _ = parse_tally_payload(payload)
        job_data = JobSubmission(**parsed_data)
        
        # Ensure config is loaded correctly for the manual script run
        from app.config import settings
        settings.whatsapp_template_name = os.getenv("WHATSAPP_TEMPLATE_NAME", "job_post_notification")
        settings.whatsapp_template_lang = os.getenv("WHATSAPP_TEMPLATE_LANG", "en_US")
        
        target_number = os.getenv("WA_ADMIN_NUMBER")
        print(f"Sending WA template to {target_number}...")
        
        msg_id, status, wa_response = await wa_client.send_template_message(target_number, job_data)
        
        print(f"Msg ID: {msg_id}")
        print(f"Status: {status}")
        with open("wa_error.json", "w") as f:
            f.write(str(wa_response))
        print(f"Raw Response written to wa_error.json")

    except Exception as e:
        print(f"Error testing direct WA client: {e}")

if __name__ == "__main__":
    asyncio.run(main())
