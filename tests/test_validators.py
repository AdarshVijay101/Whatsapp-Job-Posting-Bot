import pytest
from pydantic import ValidationError
from app.validators.guardrails import JobSubmission

def get_valid_payload():
    return {
        "submitter_name": "Jane Doe",
        "job_description_long": "We are looking for a highly skilled Senior Python Backend Developer to join our growing team. The ideal candidate will have extensive experience with FastAPI, PostgreSQL, and building scalable APIs. Responsibilities include designing and developing high-volume, low-latency applications for mission-critical systems and delivering high-availability and performance. You should be able to write well-designed, testable, and efficient code. Experience with Docker and CI/CD pipelines is a strong plus. Join us to help shape the future of our tech stack.", # >200 chars
        "force_send_even_if_missing": False
    }

def test_valid_submission():
    payload = get_valid_payload()
    job = JobSubmission(**payload)
    assert job.submitter_name == "Jane Doe"

def test_missing_required_field():
    payload = get_valid_payload()
    del payload["submitter_name"]
    with pytest.raises(ValidationError):
        JobSubmission(**payload)

def test_short_description():
    payload = get_valid_payload()
    payload["job_description_long"] = "Too short"
    with pytest.raises(ValidationError) as exc:
        JobSubmission(**payload)
    assert "String should have at least 200 characters" in str(exc.value)

def test_spam_keyword():
    payload = get_valid_payload()
    payload["job_description_long"] = payload["job_description_long"] + " guaranteed get rich quick"
    with pytest.raises(ValidationError) as exc:
        JobSubmission(**payload)
    assert "banned keywords" in str(exc.value).lower()

def test_spam_too_many_links():
    payload = get_valid_payload()
    payload["job_description_long"] = payload["job_description_long"] + " http://link1 http://link2 http://link3 http://link4"
    with pytest.raises(ValidationError) as exc:
        JobSubmission(**payload)
    assert "Too many links" in str(exc.value)

def test_spam_repeated_chars():
    payload = get_valid_payload()
    payload["job_description_long"] = payload["job_description_long"] + " HIIIIIIIII!!!!!!"
    with pytest.raises(ValidationError) as exc:
        JobSubmission(**payload)
    assert "too many repeated" in str(exc.value).lower()
