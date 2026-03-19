import requests
import json
import uuid
import time
from app.config import settings

API_URL = "http://127.0.0.1:8000"
HEADERS = {"X-Tally-Secret": settings.tally_webhook_secret}

def print_step(title):
    print(f"\n{'='*50}")
    print(f"🚀 {title}")
    print(f"{'='*50}\n")

def run_demo():
    # STEP 1: Bad Submission (Failed validation)
    print_step("STEP 1: Bad Submission (Validation Failure)")
    bad_payload = {
        "event_id": "demo-uuid",
        "data": {
            "fields": [
                {"label": "Submitter Name", "value": "A"}, # Too short
                {"label": "Job Description", "value": "Urgent! " * 5} # Banned keyword & too short
            ]
        }
    }
    
    print("Employer submits invalid form data (bit.ly, 'Urgent' keyword, too short)...")
    try:
        res1 = requests.post(f"{API_URL}/ingest", json=bad_payload, headers=HEADERS)
        print(f"Response ({res1.status_code}):\n{json.dumps(res1.json(), indent=2)}")
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API. Is Uvicorn running? (Run: uvicorn app.main:app --reload)")
        return
    
    time.sleep(2)
    
    # STEP 2: Valid Submission -> PENDING Status
    print_step("STEP 2: Valid Submission -> PENDING Queue")
    job_id = uuid.uuid4().hex[:6]
    valid_payload = {
        "event_id": "demo-uuid-2",
        "data": {
            "fields": [
                {"label": "Submitter Name", "value": f"Sarah Jenkins {job_id}"},
                {"label": "Job Description", "value": "We are seeking a highly experienced Lead Infrastructure Architect to join our enterprise cloud division. You will build highly scalable Kubernetes clusters, optimize CI/CD pipelines, and design our next-generation networking topology. You must be able to write robust Terraform scripts and collaborate closely with our security and application development teams. Experience migrating on-premise solutions to AWS is required. You will receive extensive competitive benefits. You must be a US Citizen and able to obtain a secret clearance. Join our world class teams to shape the future of enterprise architecture! Location: New York, NY (Hybrid). Salary: $160,000. Work Authorization: US Citizen. Apply at https://careers.enterprise-sys.com/apply"},
                {"label": "Force Send Even If Missing", "value": False}
            ]
        }
    }
    
    print("Employer submits valid, high-quality job post...")
    res2 = requests.post(f"{API_URL}/ingest", json=valid_payload, headers=HEADERS)
    data2 = res2.json()
    print(f"Response ({res2.status_code}):\n{json.dumps(data2, indent=2)}")
    print("\nNotice the job is accepted but NOT sent to WhatsApp yet. It is in the database awaiting admin review.")
    
    if res2.status_code != 200:
        return
        
    submission_id = data2.get("submission_id")
    if not submission_id:
        return
        
    time.sleep(3)
    
    # STEP 3: Admin Approval -> WhatsApp Send
    print_step("STEP 3: Admin Approval -> WhatsApp Dispatch")
    print(f"Admin reviews job '{submission_id}' in internal database and clicks 'Approve'...")
    
    res3 = requests.post(f"{API_URL}/approve/{submission_id}")
    print(f"Response ({res3.status_code}):\n{json.dumps(res3.json(), indent=2)}")
    print("\n✅ The WhatsApp notification has now been deployed to the Admin number!")
    
    print_step("STEP 4: Database & Sheets Verification")
    print("1. Check Google Sheets 'Submissions' tab. You will see the job entered with 'PENDING'.")
    print("2. Check the Admin's WhatsApp. You should have received the beautiful Template notification.")
    print("3. When Meta API Webhooks are active, they will ping /webhook and update the new 'DeliveryLog' sheet.")

if __name__ == "__main__":
    run_demo()
