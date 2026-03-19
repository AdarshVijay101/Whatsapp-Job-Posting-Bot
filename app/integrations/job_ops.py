import json
import logging
from typing import Dict, Any, Tuple, List
from app.config import settings
from app.validators.guardrails import ParsedJobData
from app.integrations.whatsapp import wa_client
import app.db as db

logger = logging.getLogger(__name__)

from app.tally_mapping import SYNONYMS_MAP

def parse_tally_payload(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Parses a specialized Tally webhook payload into a flattened dictionary 
    compatible with the JobSubmission Pydantic model.
    """
    normalized = {}
    seen_labels = []

    fields = payload.get("data", {}).get("fields", [])
    
    if not isinstance(fields, list):
        fields = []

    for field in fields:
        label = str(field.get("label", "")).strip().lower()
        value = field.get("value", "")
        
        # Handle array values (checkboxes, multi-select etc)
        if isinstance(value, list) and len(value) > 0:
            value = str(value[0])
        elif isinstance(value, list):
            value = ""
        else:
            # Keep as is but convert to string for pydantic if needed
            value = str(value)

        if label:
            seen_labels.append(label)
        
        mapped_key = SYNONYMS_MAP.get(label)
        if not mapped_key:
            # Try a "contains" fallback if exact match failed
            for syn_key, target in SYNONYMS_MAP.items():
                if syn_key in label:
                    mapped_key = target
                    break

        if mapped_key:
            normalized[mapped_key] = value

    if settings.debug_tally_mapping:
        logger.info(f"[DEBUG MAPPING] Received {len(fields)} fields.")
        logger.info(f"[DEBUG MAPPING] Seen Labels: {seen_labels}")
        logger.info(f"[DEBUG MAPPING] Mapped Keys: {list(normalized.keys())}")

    return normalized, seen_labels

async def approve_job_logic(submission_id: str) -> Dict[str, Any]:
    """
    Business logic for approving a job and sending WhatsApp template.
    """
    row = db.get_submission(submission_id)
    if not row:
        return {"error": "Submission not found", "status_code": 404}
        
    if row["validation_status"] not in ["PASSED", "PASSED_WITH_OVERRIDE"]:
        return {"error": "Cannot approve an invalid submission", "status_code": 400}
        
    if row["approval_status"] == "APPROVED":
        return {"error": "Already approved", "status_code": 400}
        
    if row["approval_status"] != "PENDING":
        return {"error": f"Not in PENDING state (Current: {row['approval_status']})", "status_code": 400}
        
    raw_payload = json.loads(row["raw_payload_json"])
    parsed_tally, _ = parse_tally_payload(raw_payload)
    submitter_name = parsed_tally.get("submitter_name", "Unknown")
    
    llm_json_str = row.get("llm_extracted_json")
    if not llm_json_str:
        return {"error": "Database entry missing LLM extracted JSON.", "status_code": 500}
        
    parsed_data = ParsedJobData(**json.loads(llm_json_str))
    
    posted_status = "FAILED"
    wa_message_id = None
    
    if settings.enable_whatsapp_send:
        target_number = settings.wa_admin_number
        if not target_number:
            logger.warning("No wa_admin_number specified. Skipping send.")
        else:
            recruiter_email = parsed_tally.get("recruiter_email") or "Not provided"
            msg_id, status, wa_response = await wa_client.send_template_message(
                target_number, 
                parsed_data, 
                submitter_name,
                recruiter_email=recruiter_email
            )
            logger.info("="*50)
            logger.info(f"[APPROVAL LOG] ID: {submission_id} | WA Response: {status}")
            logger.info("="*50)
            posted_status = status
            wa_message_id = msg_id
            
    db.update_submission_status(
        submission_id=submission_id,
        approval_status="APPROVED",
        whatsapp_message_id=wa_message_id,
        posted_status=posted_status
    )
    
    return {
        "submission_id": submission_id,
        "status": "APPROVED",
        "whatsapp_status": posted_status,
        "whatsapp_message_id": wa_message_id,
        "status_code": 200
    }

async def retry_job_logic(submission_id: str) -> Dict[str, Any]:
    """
    Business logic for retrying a failed WhatsApp send.
    """
    row = db.get_submission(submission_id)
    if not row:
        return {"error": "Submission not found", "status_code": 404}
        
    if row["posted_status"] != "FAILED":
        return {"error": f"Can only retry FAILED statuses. Current status: {row['posted_status']}", "status_code": 400}
        
    raw_payload = json.loads(row["raw_payload_json"])
    parsed_tally, _ = parse_tally_payload(raw_payload)
    submitter_name = parsed_tally.get("submitter_name", "Unknown")
    
    llm_json_str = row.get("llm_extracted_json")
    if not llm_json_str:
        return {"error": "Database entry missing LLM extracted JSON.", "status_code": 500}
        
    parsed_data = ParsedJobData(**json.loads(llm_json_str))
    
    posted_status = "FAILED"
    wa_message_id = None
    
    if settings.enable_whatsapp_send:
        target_number = settings.wa_admin_number
        if not target_number:
            logger.warning("No wa_admin_number specified. Skipping send.")
        else:
            recruiter_email = parsed_tally.get("recruiter_email") or "Not provided"
            msg_id, status, wa_response = await wa_client.send_template_message(
                target_number, 
                parsed_data, 
                submitter_name,
                recruiter_email=recruiter_email
            )
            posted_status = status
            wa_message_id = msg_id
            
    db.update_submission_status(
        submission_id=submission_id,
        whatsapp_message_id=wa_message_id,
        posted_status=posted_status
    )
    
    return {
        "submission_id": submission_id,
        "whatsapp_status": posted_status,
        "whatsapp_message_id": wa_message_id,
        "status_code": 200
    }
