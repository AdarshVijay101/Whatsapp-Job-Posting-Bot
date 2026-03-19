import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.config import settings
from app.validators.guardrails import ParsedJobData

client = TestClient(app)

import uuid

def get_tally_payload(randomize=True):
    title = f"Senior Python Backend Developer {uuid.uuid4().hex[:8]}" if randomize else "Senior Python Backend Developer"
    desc_long = "We are looking for a highly skilled Senior Python Backend Developer to join our growing team. The ideal candidate will have extensive experience with FastAPI, PostgreSQL, and building scalable APIs. Responsibilities include designing and developing high-volume, low-latency applications for mission-critical systems and delivering high-availability and performance. You should be able to write well-designed, testable, and efficient code. Experience with Docker and CI/CD pipelines is a strong plus. Join us to help shape the future of our tech stack. Must be US Citizen. $150k."
    return {
        "event_id": "test-uuid",
        "data": {
            "fields": [
                {"label": "Submitter Name", "value": title}, # using title as submitter to keep it random/unique
                {"label": "Job Description", "value": desc_long},
                {"label": "Force Send Even If Missing", "value": False}
            ]
        }
    }

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_ingest_no_secret():
    response = client.post("/ingest", json=get_tally_payload())
    # Fails immediately because no X-Tally-Secret header was sent
    assert response.status_code == 401

def test_ingest_bad_secret():
    response = client.post("/ingest", json=get_tally_payload(), headers={"X-Tally-Secret": "wrong_secret"})
    assert response.status_code == 401

@patch("app.main.parse_job_description", new_callable=AsyncMock)
def test_ingest_valid_payload(mock_parse):
    mock_parse.return_value = ParsedJobData(
        job_title="Senior Python Backend Developer",
        location="Remote USA",
        salary="$150k",
        work_authorization="US Citizen",
        job_summary="Great backend job.",
        required_skills=["Python", "FastAPI"],
        experience_required="Senior",
        employment_type="Full-time",
        application_link="https://example.com/apply",
        missing_fields=[]
    )
    
    payload = get_tally_payload()
    secret = settings.tally_webhook_secret
    
    response = client.post("/ingest", json=payload, headers={"X-Tally-Secret": secret})
    
    # Missing WhatsApp config causes SKIPPED, but status should be 200
    assert response.status_code == 200
    data = response.json()
    assert "submission_id" in data
    assert data["validation_status"] == "PASSED"
    assert "wa_prefill_link" in data

@patch("app.main.parse_job_description", new_callable=AsyncMock)
def test_ingest_invalid_payload_missing_fields(mock_parse):
    # This mock should not even be called because guardrails will reject it first,
    # but we patch it just in case to prevent actual API calls.
    payload = get_tally_payload()
    # Remove submitter name
    payload["data"]["fields"].pop(0)
    
    secret = settings.tally_webhook_secret
    response = client.post("/ingest", json=payload, headers={"X-Tally-Secret": secret})
    
    assert response.status_code == 400
    data = response.json()
    assert data["validation_status"] == "REJECTED"
    assert "rejection_reasons" in data
    assert any("submitter_name" in reason for reason in data["rejection_reasons"])


@patch("app.main.parse_job_description", new_callable=AsyncMock)
@patch("app.integrations.whatsapp.httpx.AsyncClient.post")
def test_whatsapp_template_payload(mock_post, mock_parse):
    # Mock LLM Parsed Result
    mock_parse.return_value = ParsedJobData(
        job_title="Senior Python Backend Developer",
        location="Remote USA",
        salary="$150k",
        work_authorization="US Citizen",
        job_summary="Great backend job.",
        required_skills=["Python", "FastAPI"],
        experience_required="Senior",
        employment_type="Full-time",
        application_link="https://example.com/apply",
        missing_fields=[]
    )

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"messages": [{"id": "wamid.123"}]}
    mock_post.return_value = mock_response
    
    # Temporarily override settings to force enabled
    original_token = settings.whatsapp_access_token
    original_phone_id = settings.whatsapp_phone_number_id
    original_enable = settings.enable_whatsapp_send
    original_admin = settings.wa_admin_number

    try:
        settings.whatsapp_access_token = "fake_token"
        settings.whatsapp_phone_number_id = "12345"
        settings.enable_whatsapp_send = True
        settings.wa_admin_number = "1234567890"
        
        # Also need to re-init wa_client because they pull from settings in __init__
        from app.integrations.whatsapp import wa_client
        wa_client.access_token = "fake_token"
        wa_client.phone_number_id = "12345"

        payload = get_tally_payload()
        secret = settings.tally_webhook_secret
        
        response = client.post("/ingest", json=payload, headers={"X-Tally-Secret": secret})
        
        assert response.status_code == 200
        data = response.json()
        submission_id = data["submission_id"]
        
        # Verify ingest did NOT send
        assert not mock_post.called
        
        # Now trigger approval
        approve_response = client.post(f"/approve/{submission_id}")
        assert approve_response.status_code == 200
        
        # Verify the mock was called correctly
        assert mock_post.called
        called_args, called_kwargs = mock_post.call_args
        sent_json = called_kwargs.get("json", {})
        
        assert sent_json.get("type") == "template"
        assert "template" in sent_json
        assert sent_json["template"].get("name") == "job_post_notification"
        assert sent_json["template"].get("language", {}).get("code") == "en"
        
        # Check component params
        components = sent_json["template"].get("components", [])
        assert len(components) == 1
        params = components[0].get("parameters", [])
        assert len(params) == 7
        
        # Verify each parameter only has the required keys and uses parameter_name
        expected_names = ["job_title", "location", "salary", "work_authorization", "submitter_name", "job_summary", "application_link"]
        for i, param in enumerate(params):
            assert set(param.keys()) == {"type", "parameter_name", "text"}
            assert param["type"] == "text"
            assert param["parameter_name"] == expected_names[i]
        
    finally:
        # Clean up
        settings.whatsapp_access_token = original_token
        settings.whatsapp_phone_number_id = original_phone_id
        settings.enable_whatsapp_send = original_enable
        settings.wa_admin_number = original_admin
        from app.integrations.whatsapp import wa_client
        wa_client.access_token = original_token
        wa_client.phone_number_id = original_phone_id

def test_webhook_verify_success():
    expected_challenge = "12345"
    token = settings.whatsapp_webhook_verify_token
    response = client.get(f"/webhook?hub.mode=subscribe&hub.challenge={expected_challenge}&hub.verify_token={token}")
    assert response.status_code == 200
    assert response.text == expected_challenge

def test_webhook_verify_failure():
    response = client.get(f"/webhook?hub.mode=subscribe&hub.challenge=1234&hub.verify_token=wrong_token")
    assert response.status_code == 403

def test_webhook_receive():
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {
                                    "id": "wamid.123",
                                    "status": "delivered",
                                    "timestamp": "123456789",
                                    "recipient_id": "12345"
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "received"
