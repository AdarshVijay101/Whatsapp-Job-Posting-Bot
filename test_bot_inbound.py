import requests
import json
import time

# Configuration
WEBHOOK_URL = "http://127.0.0.1:8000/webhook"
ADMIN_NUMBER = "13027728945"

def simulate_inbound_message(from_number: str, text: str):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550001111",
                                "phone_number_id": "123456789"
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test Admin"},
                                    "wa_id": from_number
                                }
                            ],
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": "wamid.HBgLMTMwMjc3Mjg5NDVGAhIAEhgUM0EBQUI0RUQ1RTk2QjREOEYzODUA",
                                    "timestamp": str(int(time.time())),
                                    "text": {"body": text},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    print(f"\n--- Simulating Message from {from_number}: '{text}' ---")
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # 1. Test HELP
    simulate_inbound_message(ADMIN_NUMBER, "HELP")
    
    # 2. Test LIST PENDING
    simulate_inbound_message(ADMIN_NUMBER, "LIST PENDING")
    
    # 3. Test Unauthorized
    simulate_inbound_message("15550009999", "APPROVE dummy-id")
    
    # 4. Test Normalization (Simulate message from a "messy" number if Meta allowed it, 
    # but Meta usually sends clean numbers like '13027728945')
    # Let's just verify the logic works for the allowlist.
