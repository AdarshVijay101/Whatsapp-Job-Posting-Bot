import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_validate_job():
    print("Testing /validate-job endpoint...")
    
    # Needs a long description
    long_desc = "We are looking for a Senior Software Engineer with at least 5 years of experience in Python and React. The role is a full-time position located in London, UK. Salary is £80,000 - £100,000 per year. You must have valid work authorization for the UK. Apply at https://tillianai.com/jobs/123"
    
    payload = {
        "job_description": long_desc,
        "submitter_name": "Test Runner"
    }
    
    try:
        # First call (should be slow/LLM)
        start = time.time()
        resp = requests.post(f"{BASE_URL}/validate-job", json=payload)
        end = time.time()
        print(f"First call took: {end - start:.2f}s")
        print(f"Status: {resp.status_code}")
        print(f"Result: {json.dumps(resp.json(), indent=2)}")
        
        # Second call (should be hit cache)
        start = time.time()
        resp2 = requests.post(f"{BASE_URL}/validate-job", json=payload)
        end = time.time()
        print(f"Second call (cached) took: {end - start:.2f}s")
        assert end - start < 0.1, "Cache hit should be fast"
        
        # Test rate limiting
        print("Testing rate limiting (should trigger 429)...")
        resp3 = requests.post(f"{BASE_URL}/validate-job", json=payload)
        print(f"Status: {resp3.status_code}")
        if resp3.status_code == 429:
            print("Rate limiting working correctly.")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    # Note: Backend must be running for this test
    # uvicorn app.main:app --port 8000
    test_validate_job()
