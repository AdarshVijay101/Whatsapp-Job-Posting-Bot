import asyncio
import uuid
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock
from app.main import ingest_job
from app.config import settings
import logging

# Set up logging to console
logging.setLoggerClass(logging.Logger)
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)
# Clear existing handlers
for h in logger.handlers[:]:
    logger.removeHandler(h)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

async def test_ingest_logic():
    print("--- Starting Local Ingest Verification (Force-Override Mode) ---")
    
    # 1. Prepare payload with force_send=True to ensure 200 OK
    payload = {
        "event_id": str(uuid.uuid4()),
        "data": {
            "fields": [
                {"label": "Submitter Name", "value": "Verification Bot"},
                {"label": "Force Send Even If Missing", "value": True},
                {"label": "Job Description", "value": "We are seeking a senior DevOps engineer. This is a short description for verification purposes to ensure the force-override logic correctly pads missing fields with N/A and logs successfully to both SQLite and Google Sheets."}
            ]
        }
    }
    
    # 2. Mock FastAPI Request
    mock_request = MagicMock()
    mock_request.headers = {"X-Tally-Secret": settings.tally_webhook_secret}
    
    async def get_json():
        return payload
    mock_request.json = get_json
    
    # 3. Call ingest_job
    try:
        response = await ingest_job(mock_request)
        print(f"\nAPI Response Status: {response.status_code}")
        body = json.loads(response.body.decode())
        print(f"API Response Body: {json.dumps(body, indent=2)}")
        
        if response.status_code == 200:
            print("\nSUCCESS: End-to-End Logic Succeeded!")
            print("Check Google Sheets 'Submissions' tab for the new entry.")
        else:
            print(f"\nFAILURE: Ingest returned status {response.status_code}")
            
    except Exception as e:
        print(f"\nERROR: Execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ingest_logic())
