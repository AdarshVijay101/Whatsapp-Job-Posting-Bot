import re
import hashlib
from urllib.parse import urlparse
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator, field_serializer

# Configurable banned keywords list
BANNED_KEYWORDS = ["urgent", "guaranteed", "no experience required", "get rich quick", "fee required", "pay to apply"]

class JobSubmission(BaseModel):
    """Raw, normalized payload directly from Tally form."""
    submitter_name: str = Field(..., min_length=2)
    recruiter_email: Optional[str] = None
    job_description: str = Field(..., min_length=180, description="Minimum 180 characters")
    force_send_even_if_missing: bool = False

    @field_validator('job_description')
    @classmethod
    def validate_content_safety(cls, v: str) -> str:
        text_lower = v.lower()
        
        # 1. Check banned keywords
        found_banned = [w for w in BANNED_KEYWORDS if w in text_lower]
        if found_banned:
            raise ValueError(f"Description contains banned keywords: {', '.join(found_banned)}")
            
        # 2. Check for max URLs (e.g. <= 3 http occurrences)
        link_count = text_lower.count("http")
        if link_count > 3:
            raise ValueError("Too many links in description (max 3 allowed)")
            
        # 3. Check repeated characters heuristic
        if re.search(r'(.)\1{4,}', text_lower):
            raise ValueError("Spam pattern detected (too many repeated characters)")

        return v


    def generate_hash(self) -> str:
        # Avoid duplicates based on description slice and submitter
        desc_slice = self.job_description[:50].lower().strip()
        data = f"{self.submitter_name.lower().strip()}|{desc_slice}"
        return hashlib.sha256(data.encode()).hexdigest()

class ParsedJobData(BaseModel):
    """Strict JSON structure enforced upon the OpenAI API response."""
    job_title: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    work_authorization: Optional[str] = None
    job_summary: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    experience_required: Optional[str] = None
    employment_type: Optional[str] = None
    application_link: Optional[str] = None
    missing_fields: List[str] = Field(default_factory=list)

    @field_serializer('application_link')
    def serialize_url(self, url: HttpUrl | str | None):
        return str(url) if url else None


