import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv

# Add parent directory to path to import app modules if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.tally_mapping import SYNONYMS_MAP
    from app.config import settings
except ImportError:
    print("Error: Could not import app modules. Run this from the project root.")
    sys.exit(1)

def run_tally_check():
    print("="*60)
    print("🔍 TALLY INTEGRATION SETUP CHECK")
    print("="*60)

    # 1. Environment & Secrets
    print("\n[1] Environment & Secrets")
    secret = settings.tally_webhook_secret
    if not secret:
        print("❌ TALLY_WEBHOOK_SECRET is MISSING in .env")
    else:
        print(f"✅ TALLY_WEBHOOK_SECRET is SET: {secret[:4]}****")

    # 2. Form Labels & Mapping
    print("\n[2] Expected Tally Form Labels")
    print("Your Tally form should use these EXACT labels (or close synonyms):")
    
    # Priority labels we care about
    core_labels = ["Submitter Name", "Job Description", "Force Send Even If Missing"]
    for label in core_labels:
        # Check if label is in SYNONYMS_MAP
        found = False
        for syn in SYNONYMS_MAP:
            if syn in label.lower() or label.lower() in syn:
                found = True
                break
        status = "✅ Found in mapping" if found else "❌ MISSING in app/tally_mapping.py"
        print(f"  - {label.ljust(30)} {status}")

    # 3. Endpoint Readiness
    print("\n[3] Local Endpoint Readiness")
    print("Checking if local server is running on http://localhost:8000...")
    try:
        response = requests.get("http://localhost:8000/tally-health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Local server is UP!")
            print(f"   Endpoint Type: {data.get('endpoint')}")
            print(f"   Auth Required: {data.get('auth_header_required')}")
        else:
            print(f"⚠️  Local server returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Local server is NOT responding. Run: uvicorn app.main:app --reload")

    # 4. Tally Webhook Settings
    print("\n[4] Tally Webhook Config Instructions")
    print("In your Tally form settings -> Webhooks:")
    print(f"  - Webhook URL: <Your-NGROK-URL>/ingest")
    print(f"  - Method:      POST")
    print(f"  - Custom Headers:")
    print(f"    Key:   X-Tally-Secret")
    print(f"    Value: {secret if secret else 'MISSING'}")

    print("\n" + "="*60)
    print("💡 TIP: If you change form labels, RE-PUBLISH the Tally form.")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_tally_check()
