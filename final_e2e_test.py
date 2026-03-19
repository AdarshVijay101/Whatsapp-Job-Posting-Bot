import requests
import json
import uuid

# Configuration
TUNNEL_URL = "https://consoles-sewing-bacterial-favor.trycloudflare.com"
TALLY_SECRET = "a5546d50-a0dc-4f76-8d04-a708df8dc9ea"

def run_final_test():
    print(f"--- Starting Final End-to-End Verification via {TUNNEL_URL} ---")
    
    # 1. Ingest Payload
    ingest_url = f"{TUNNEL_URL}/ingest"
    headers = {"X-Tally-Secret": TALLY_SECRET}
    payload = {
        "event_id": str(uuid.uuid4()),
        "data": {
            "fields": [
                {"label": "Submitter Name", "value": "Final E2E Bot"},
                {"label": "Force Send Even If Missing", "value": True},
                {"label": "Job Description", "value": "We are seeking a senior AI specialist to join our innovative team in Manhattan. You will work on cutting-edge agentic workflows and LLM integrations. This description is optimized for the final verification of the production-ready WhatsApp Job Poster backend. Salary: $180,000. Location: New York, NY. Apply at https://example.com/ai-careers"}
            ]
        }
    }
    
    print(f"Post to /ingest...")
    try:
        r1 = requests.post(ingest_url, json=payload, headers=headers)
        print(f"Ingest Status: {r1.status_code}")
        res1 = r1.json()
        print(f"Response: {json.dumps(res1, indent=2)}")
        
        if r1.status_code != 200:
            print("❌ Ingest Failed")
            return
            
        submission_id = res1.get("submission_id")
        print(f"✅ Ingest Succeeded. Submission ID: {submission_id}")
        
        # 2. Approve Job
        approve_url = f"{TUNNEL_URL}/approve/{submission_id}"
        print(f"\nApprove Submission {submission_id}...")
        r2 = requests.post(approve_url)
        print(f"Approve Status: {r2.status_code}")
        res2 = r2.json()
        print(f"Response: {json.dumps(res2, indent=2)}")
        
        if r2.status_code == 200:
            print("\n🎉 FINAL END-TO-END VERIFICATION SUCCESSFUL!")
            print("The WhatsApp message should have been dispatched.")
        else:
            print("❌ Approval/Send Failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_final_test()
