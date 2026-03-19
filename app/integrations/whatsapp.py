import logging
import httpx
from typing import Tuple, Optional, Any
from app.config import settings
from app.validators.guardrails import ParsedJobData

logger = logging.getLogger(__name__)

class WhatsAppClient:
    def __init__(self):
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.access_token = settings.whatsapp_access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
    async def send_text_message(self, to_number: str, text: str) -> Tuple[Optional[str], str, str]:
        """
        Sends a WhatsApp text message.
        Returns Tuple: (message_id_if_success, status_string, raw_response_or_error_string)
        """
        if not self.access_token or not self.phone_number_id:
            logger.warning("WhatsApp credentials missing. Skipping actual send attempt.")
            return None, "SKIPPED", "Missing credentials"
            
        url = f"https://graph.facebook.com/{settings.whatsapp_api_version}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number.replace("+", ""),  # Cloud API expects purely digits
            "type": "text",
            "text": {"preview_url": False, "body": text}
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
            
            resp_data = response.json()
            if response.status_code in (200, 201):
                msg_id = resp_data.get("messages", [{}])[0].get("id")
                return msg_id, "SENT", str(resp_data)
            else:
                logger.error(f"WhatsApp API Error {response.status_code}: {resp_data}")
                return None, "FAILED", str(resp_data)
                
        except Exception as e:
            logger.exception("Failed to send WhatsApp message")
            return None, "FAILED", str(e)

    async def send_template_message(self, to_number: str, parsed_data: ParsedJobData, submitter_name: str, recruiter_email: str = "Omitted", prime_vendor: str = "Tillian AI") -> Tuple[Optional[str], str, Any]:
        """
        Sends a WhatsApp template message with the structured OpenAI outputs.
        Returns Tuple: (message_id_if_success, status_string, raw_response_or_error_data)
        """
        if not self.access_token or not self.phone_number_id:
            logger.warning("WhatsApp credentials missing. Skipping actual send attempt.")
            return None, "SKIPPED", "Missing credentials"
            
        url = f"https://graph.facebook.com/{settings.whatsapp_api_version}/{self.phone_number_id}/messages"

        # The parameters must follow the order/count in the approved Meta template.
        # Based on live_template.json (7 NAMED PARAMS): job_title, location, salary, work_authorization, submitter_name, job_summary, application_link
        parameters = [
            {"type": "text", "parameter_name": "job_title", "text": str(parsed_data.job_title or "N/A")},
            {"type": "text", "parameter_name": "location", "text": str(parsed_data.location or "N/A")},
            {"type": "text", "parameter_name": "salary", "text": str(parsed_data.salary or "TBD")},
            {"type": "text", "parameter_name": "work_authorization", "text": str(parsed_data.work_authorization or "N/A")},
            {"type": "text", "parameter_name": "submitter_name", "text": str(submitter_name)},
            {"type": "text", "parameter_name": "job_summary", "text": str(parsed_data.job_summary or "N/A")},
            {"type": "text", "parameter_name": "application_link", "text": str(parsed_data.application_link or "N/A")}
        ]

        # Use configured lang first, then typical fallbacks
        base_lang = settings.whatsapp_template_lang
        languages_to_try = [base_lang]
        for fallback in ["en_US", "en", "en_GB"]:
            if fallback not in languages_to_try:
                languages_to_try.append(fallback)

        last_error = ""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for lang_code in languages_to_try:
                    payload = {
                        "messaging_product": "whatsapp",
                        "to": to_number.replace("+", ""),
                        "type": "template",
                        "template": {
                            "name": settings.whatsapp_template_name,
                            "language": {"code": lang_code},
                            "components": [
                                {
                                    "type": "body",
                                    "parameters": parameters
                                }
                            ]
                        }
                    }
                    
                    import json
                    with open("payload_success.json", "w") as f:
                        json.dump(payload, f, indent=2)

                    response = await client.post(url, json=payload, headers=self.headers)
                    resp_data = response.json()
                    
                    if response.status_code in (200, 201):
                        msg_id = resp_data.get("messages", [{}])[0].get("id")
                        return msg_id, "SENT", resp_data
                    else:
                        # Check if it's specifically a template language missing error
                        err_code = resp_data.get("error", {}).get("code")
                        if err_code == 132001:
                            logger.warning(f"Template '{settings.whatsapp_template_name}' not found for language '{lang_code}'. Retrying fallback...")
                            last_error = str(resp_data)
                            continue  # Try the next language 
                        else:
                            # If it's a different error (like invalid token), fail immediately
                            logger.error(f"WhatsApp API Error {response.status_code}: {resp_data}")
                            return None, "FAILED", str(resp_data)

                # If we exhausted all fallbacks
                logger.error(f"WhatsApp API Error: Exhausted all template language fallbacks. Last error: {last_error}")
                return None, "FAILED", last_error
                
        except Exception as e:
            logger.exception("Failed to send WhatsApp template message")
            return None, "FAILED", str(e)

# Global instances for easy import
wa_client = WhatsAppClient()
