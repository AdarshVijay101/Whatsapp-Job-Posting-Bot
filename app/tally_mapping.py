"""
This file contains the synonyms mapping used to map incoming Tally form labels 
to the internal JobSubmission fields.

Non-developers can safely add or edit entries in the SYNONYMS_MAP dictionary.
Make sure all keys (the incoming Tally labels) are entirely lowercase.
"""

SYNONYMS_MAP = {
    # 1. Submitter details
    "submitter name": "submitter_name",
    "posted by": "submitter_name",
    "recruiter name": "submitter_name",
    "vendor name": "submitter_name",
    "prime vendor": "submitter_name",
    "recruiter email": "recruiter_email",
    "email": "recruiter_email",

    # 2. Main unstructured block
    "job description": "job_description",
    "description": "job_description",
    "details": "job_description",
    "job details": "job_description",
    "role description": "job_description",
    "full job description": "job_description",

    # 3. Explicit override toggle
    "force send even if missing": "force_send_even_if_missing",
    "force send": "force_send_even_if_missing",
    "send incomplete": "force_send_even_if_missing",
    "override missing fields": "force_send_even_if_missing",
}
