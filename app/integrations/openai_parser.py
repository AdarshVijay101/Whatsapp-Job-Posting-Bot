import logging
import json
import re
from typing import Dict, Any, List
from openai import AsyncOpenAI
from app.config import settings
from app.validators.guardrails import JobSubmission, ParsedJobData

logger = logging.getLogger(__name__)

# Initialize client only if enabled
aclient = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

async def parse_job_description(submission: JobSubmission) -> ParsedJobData:
    """
    Sends the long job description and explicitly provided fields to OpenAI for structured parsing.
    Returns a unified ParsedJobData object.
    """
    if not settings.enable_openai_parse or not aclient:
        logger.error("OpenAI parsing called but disabled or missing API key.")
        raise ValueError("OpenAI parsing is misconfigured.")

    # We must explicitly tell the LLM to extract all structured data from the single block of text.
    system_prompt = """
You are a highly accurate data extraction assistant handling technical job postings.
Your task is to extract job details and format them strictly into the requested JSON schema.

CRITICAL RULES:
1. You will be provided with a SUBMITTER NAME and a LONG JOB DESCRIPTION.
2. The LONG JOB DESCRIPTION contains all the necessary job posting facts. Do not invent or hallucinate values.
3. You MUST attempt to extract the following critical fields natively from the text:
   - job_title
   - location
   - salary
   - work_authorization
   - application_link
4. If any of the above 5 fields are completely missing, ambiguous, or not present, return null for that field.
5. `job_summary` should be a concise, professional 2-3 sentence summary (WhatsApp friendly).
6. `missing_fields`: Analyze your final extracted object. If any of [job_title, location, salary, work_authorization, application_link] are fully null/empty, push those exact key names into the `missing_fields` array.
"""

    user_content = f"""
EXPLICIT FIELDS PROVIDED:
- Submitter Name: {submission.submitter_name}

LONG JOB DESCRIPTION:
{submission.job_description}
"""

    try:
        completion = await aclient.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format=ParsedJobData,
            temperature=0.0
        )
        
        parsed: ParsedJobData = completion.choices[0].message.parsed
        
        # Manually ensure missing_fields array is accurate (LLMs sometimes miss appending to arrays)
        required_keys = ["job_title", "location", "salary", "work_authorization", "application_link"]
        actual_missing = []
        for key in required_keys:
            val = getattr(parsed, key, None)
            if not val or (isinstance(val, str) and not val.strip()):
                actual_missing.append(key)
                
        parsed.missing_fields = list(set(parsed.missing_fields + actual_missing))
        
        # Word cleanup helper for job_summary (limit 200 words)
        if parsed.job_summary:
            norm = re.sub(r'\s+', ' ', parsed.job_summary).strip()
            words = norm.split(' ')
            if len(words) > 200:
                parsed.job_summary = ' '.join(words[:200]) + "..."
            else:
                parsed.job_summary = norm
                
        return parsed

    except Exception as e:
        logger.exception("OpenAI structured extraction failed.")
        raise
